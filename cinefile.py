import os
import re
import traceback
import urllib.request
import requests
import tmdbsimple as tmdb
from PIL import Image
from guessit import guessit
import threading

tmdb.API_KEY = "6a4bc831d3389b694627785af6f5320e"


def check_connection(url='https://www.themoviedb.org/', timeout=5):
    try:
        r = requests.head(url, timeout=timeout)
        return True
    except requests.ConnectionError as ex:
        return False


class Movie:  # just pass movie file address as input, failed will be True if some problem happens
    failed = False
    search = tmdb.Search()
    name = None
    year = None
    abspath = None
    director = None
    director_icon = None
    id = None
    poster_path = None
    folder_path = None

    def __init__(self, movie_file=None):
        if movie_file is not None:
            if os.path.isfile(movie_file):
                try:
                    self.init_name(movie_file)
                    self.find_details()
                    self.failed = True if self.name is None or self.year is None or self.id is None or self.director is None \
                        else False
                except Exception as exc:
                    print(traceback.format_exc())
                    print (movie_file, self.name, self.year, self.id)
                    self.failed = True

    def init_name(self, movie_file):
        newname = re.sub("[_.-]", " ", os.path.basename(movie_file))
        findall = re.findall(r"\d{4}", newname)
        if "1080" in findall:
            findall.remove("1080")

        self.year = int(findall[-1])
        self.name = re.split(str(self.year), newname)[0].strip()
        self.abspath = os.path.abspath(movie_file).strip()

    def find_details(self):
        self.search.movie(query=self.name)

        for movie in self.search.results:
            try:
                result_year = int(re.split('-', movie['release_date'])[0])
            except:
                result_year = None

            if result_year is not None:
                if self.year == result_year:
                    self.id = int(movie['id'])
                    self.poster_path = movie['poster_path']
                    break

        movie = tmdb.Movies(self.id)
        for personnel in movie.credits()['crew']:
            if personnel['job'] == "Director":
                self.director = personnel['name'].strip().encode("utf-8")
                self.director_icon = personnel['profile_path']
                break

    def __str__(self):
        return str(self.name) + " " + str(self.year) + " : " + self.director.decode('utf-8')


class MovieScanner:  # pass working folder path
    status = ""  # Send Status For GUI
    total_progress = 0  # Progress Bar Data for GUI
    done_progress = 0
    movie_list = list()
    threads = list()
    director_icons = dict()  # Director name to director picture
    folder_pattern = "{YEAR} - {MOVIENAME}"  # like (2011 - Melancholia), pattern can be changed
    formats = ["mp4", "mkv", "avi", "flv", "avi", "wmv"]  # can be changed
    exclude_folders = list()
    rec_search = False  # Search Recursively ?

    def __init__(self, basefolder):
        self.basefolder = basefolder
        self.work_folder = os.path.join(self.basefolder, "CineFile")

    @staticmethod
    def count_progress(folder):
        total_progress = 0
        for item in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, item)):
                total_progress += MovieScanner.count_progress(os.path.join(folder, item))
            else:
                total_progress += 1

        return total_progress

    def set_workfolder(self, work_folder):
        self.work_folder = os.path.join(self.basefolder, work_folder)

    def exclude(self, folder_list):  # a string -> folder1,folder2,folder3,folder4
        fold_list = re.split(r",", folder_list)
        for folder_name in fold_list:
            self.exclude_folders.append(folder_name.strip())

    def myfunc(self, folder, i):
        if re.split(r"\.", i)[-1] in self.formats:
            movie = Movie(folder + i)
            if not movie.failed:
                self.status = "Recognized " + str(movie)
                print(self.status)
                self.director_icons[movie.director] = movie.director_icon
                movie.folder_path = os.path.join(self.work_folder, movie.director.decode('utf-8'),
                                                    self.generate_fname(movie))
                self.movie_list.append(movie)
            else:
                del movie

    def scan_folder(self, folder=None):  # check self.movie_list afterwards!
        self.total_progress = MovieScanner.count_progress(self.basefolder)
        folder = self.basefolder if folder is None else folder
        folder = folder + os.path.sep
        listd = os.listdir(folder)

        for i in listd:
            try:
                if os.path.isdir(folder + i) and i not in self.exclude_folders:
                    if self.rec_search:
                        self.scan_folder(folder + i)
                else:
                    t = threading.Thread(target=self.myfunc, args=(folder, i,))
                    self.threads.append(t)
                    t.start()
                    # if re.split(r"\.", i)[-1] in self.formats:
                    #     movie = Movie(folder + i)
                    #     if not movie.failed:
                    #         self.status = "Recognized " + str(movie)
                    #         print(self.status)
                    #         self.director_icons[movie.director] = movie.director_icon
                    #         movie.folder_path = os.path.join(self.work_folder, movie.director.decode('utf-8'),
                    #                                          self.generate_fname(movie))
                    #         self.movie_list.append(movie)
                    #     else:
                    #         del movie
                self.done_progress += 1
            except Exception as exc:
                print(traceback.format_exc())
                print(exc)

    
    def generate_fname(self, movie):  # generates folder name
        out = self.folder_pattern.replace("{YEAR}", str(movie.year)).replace("{MOVIENAME}", movie.name)
        return out

    def make_folders(self):  # Should scan folder first, movie_list should not be empty
        self.total_progress = len(self.movie_list)
        try:
            if not os.path.isdir(self.work_folder):
                os.mkdir(self.work_folder)

        except Exception as exc:
            print(traceback.format_exc())
            print(exc)
            self.status = "Problem working with folder"
            print(self.status)
            return

        for movie in self.movie_list:
            movie_dir = movie.folder_path

            try:
                if os.path.isdir(os.path.join(self.work_folder, movie.director.decode('utf-8'))):
                    if not os.path.isdir(movie_dir):
                        os.mkdir(movie_dir)
                else:
                    os.mkdir(os.path.join(self.work_folder, movie.director.decode('utf-8')))
                    os.mkdir(movie_dir)

                if not os.path.isfile(os.path.join(movie_dir, os.path.basename(movie.abspath))):
                    os.rename(movie.abspath, os.path.join(movie_dir, os.path.basename(movie.abspath)))
                    movie.abspath = os.path.join(movie_dir, os.path.basename(movie.abspath))
                self.done_progress += 1

            except Exception as exc:
                print(traceback.format_exc())
                print(exc)
                self.status = "Problem Writing the File"
                print(self.status)

    def icon_thread(self, movie):
        url = urllib.request.urlopen("https://image.tmdb.org/t/p/w200/" + movie.poster_path)
        im = Image.open(url).convert('RGBA')
        im_new = Icon.expand2square(im)
        im_new.save(os.path.join(movie.folder_path, "icon.ico"))
        os.system("attrib +H \"" + os.path.join(movie.folder_path, "icon.ico\""))
        Icon.set_icon(movie.folder_path, self)
        self.done_progress += 1


    def set_icons(self):  # should make_folders first
        self.total_progress = len(self.movie_list)
        self.threads = list()

        for movie in self.movie_list:
            if movie.poster_path is None or movie.folder_path is None or \
                    os.path.isfile(os.path.join(movie.folder_path, "icon.ico")):
                self.done_progress += 1
                continue

            try:
                t = threading.Thread(target=self.icon_thread, args=(movie,))
                self.threads.append(t)
                t.start()
                # url = urllib.request.urlopen("https://image.tmdb.org/t/p/w200/" + movie.poster_path)
                # im = Image.open(url).convert('RGBA')
                # im_new = Icon.expand2square(im)
                # im_new.save(os.path.join(movie.folder_path, "icon.ico"))
                # os.system("attrib +H \"" + os.path.join(movie.folder_path, "icon.ico\""))
                # Icon.set_icon(movie.folder_path, self)
                # self.done_progress += 1

            except Exception as exc:
                print(traceback.format_exc())
                print(exc)
                self.status = "Problem making the movie icon"
                print(self.status)


class Icon:
    desktopini = '[.ShellClassInfo] \nIconResource=icon.ico,0 \n'

    def __init__(self):
        pass

    @staticmethod
    def expand2square(pil_img, background_color=0):  # copied this from note.nkmk.me
        width, height = pil_img.size
        if width == height:
            return pil_img
        elif width > height:
            result = Image.new(pil_img.mode, (width, width), background_color)
            result.paste(pil_img, (0, (width - height) // 2))
            return result
        else:
            result = Image.new(pil_img.mode, (height, height), background_color)
            result.paste(pil_img, ((height - width) // 2, 0))
            return result

    @staticmethod
    def set_icon(folderpath, object=None):

        if object is not None:
            object.status = "Setting Icon for " + os.path.abspath(folderpath)
            print(object.status)
        try:
            if not os.path.isfile(os.path.join(folderpath, "desktop.ini")):
                with open(os.path.join(folderpath, "desktop.ini"), "w") as f:
                    f.write(Icon.desktopini)
                    f.close()

        except Exception as exc:
            print(traceback.format_exc())
            print(exc)
            if object is not None:
                object.status = "Problem in writing desktop.ini"
                print(object.status)

        try:
            os.system('attrib +S +H "' + os.path.join(folderpath, 'desktop.ini"'))
            os.system('attrib +R "' + folderpath + '"')

        except Exception as exc:
            print(traceback.format_exc())
            print(exc)
            object.status = "Problem with setting icon"
            print(object.status)

    @staticmethod
    def clear_iconcache():
        try:
            os.system("taskkill /f /im explorer.exe")
            os.system(r'attrib -h -s -r "%userprofile%\AppData\Local\IconCache.db"')
            os.system(r'del /f "%userprofile%\AppData\Local\IconCache.db"')
            os.system(r'attrib /s /d -h -s -r "%userprofile%\AppData\Local\Microsoft\Windows\Explorer\*"')
            os.system(r'del /f "%userprofile%\AppData\Local\Microsoft\Windows\Explorer\\thumbcache_*.db"')
            os.system(r"start explorer")


        except:
            pass


class DirectorIcon:  # pass Directors folder, like CineFile folder
    status = ""
    total_progress = 0
    done_progress = 0
    threads = list()
    director_icons = dict()  # { links folder path to jpg URL }

    def __init__(self, basefolder):
        self.basefolder = basefolder

    def scan_folder(self, movie_scanner=None): 
        listd = os.listdir(self.basefolder)
        self.total_progress = len(listd)

        for item in listd:
            self.status = "checking folder " + os.path.join(self.basefolder, item)
            try:
                t = threading.Thread(target=self.validate_director, args=(item, movie_scanner,))
                self.threads.append(t)
                t.start()
                self.done_progress += 1
            except Exception as exc:
                print(traceback.format_exc())
                print(exc)
                self.status = "Problem with API"
                print(self.status)

    def validate_director(self, name, movie_scanner=None):

        if movie_scanner is not None:
            if name in movie_scanner.director_icons:
                self.director_icons[os.path.join(self.basefolder, name)] = movie_scanner.director_icons[name]
                self.status = "Recognized " + name
                print(self.status)
                return

        search = tmdb.Search()
        person = search.person(query=name)
        if person['total_results'] != 0:
            self.director_icons[os.path.join(self.basefolder, name)] = person['results'][0]['profile_path']
            self.status = "Recognized " + name
            print(self.status)

    def icon_thread(self, folderpath):
        url = urllib.request.urlopen("https://image.tmdb.org/t/p/w200/" + self.director_icons[folderpath])
        im = Image.open(url).convert('RGBA')
        im_new = Icon.expand2square(im)
        im_new.save(os.path.join(folderpath, "icon.ico"))
        os.system("attrib +H \"" + os.path.join(folderpath, "icon.ico\""))
        Icon.set_icon(folderpath, self)
    
    def set_icons(self):  # should scan first, director_icons should not be empty
        self.threads.clear()
        for folderpath in self.director_icons:
            self.status = "setting icon for " + folderpath
            if self.director_icons[folderpath] is None or os.path.isfile(os.path.join(folderpath, "icon.ico")):
                continue
            try:
                t = threading.Thread(target=self.icon_thread, args=(str(folderpath),))
                self.threads.append(t)
                t.start()

            except Exception as exc:
                print(traceback.format_exc())
                print(exc)
                self.status = "Problem making the movie icon"
                print(self.status)


class TV:
    failed = False
    name = None
    season = None
    episode = None
    abspath = None

    def __init__(self, tv_file=None):
        if tv_file is not None:
            if os.path.isfile(tv_file):
                try:
                    self.init_name(tv_file)
                    self.failed = True if self.name is None or self.episode is None else False

                except Exception as exc:
                    self.failed = True


    def init_name(self, tv_file):
        guess = guessit(os.path.basename(tv_file))
        self.name = guess['title'].strip()
        if 'season' in guess:
            self.season = str(guess['season'])
        self.episode = str(guess['episode'])
        self.abspath = os.path.abspath(tv_file).strip()

    def __str__(self):
        return str(self.name) + " S" + str(self.season) + " E" + str(self.episode)


class TVScanner:  # pass working folder path
    status = ""  # Send Status For GUI
    total_progress = 0  # Progress Bar Data for GUI
    done_progress = 0
    formats = ["mp4", "mkv", "avi", "flv", "avi", "wmv", "srt"]  # can be changed
    exclude_folders = list()
    threads = list()
    rec_search = False  # Search Recursively ?

    def __init__(self, basefolder):
        self.basefolder = basefolder
        self.work_folder = os.path.join(self.basefolder, "CineFile - Series")

    def exclude(self, folder_list):  # a string -> folder1,folder2,folder3,folder4
        fold_list = re.split(r",", folder_list)
        for folder_name in fold_list:
            self.exclude_folders.append(folder_name.strip())

    def scan_folder(self, folder=None):  
        self.total_progress = MovieScanner.count_progress(self.basefolder)
        folder = self.basefolder if folder is None else folder
        folder = folder + os.path.sep
        listd = os.listdir(folder)

        for i in listd:
            try:
                if os.path.isdir(folder + i) and i not in self.exclude_folders:
                    if self.rec_search:
                        self.scan_folder(folder + i)
                else:
                    if re.split(r"\.", i)[-1] in self.formats:
                        tv = TV(folder + i)
                        if not tv.failed:
                            self.status = "Recognized " + str(tv)
                            print(self.status)
                            self.make_folder(tv)
                        else:
                            del tv
                self.done_progress += 1
            except Exception as exc:
                print(traceback.format_exc())
                print(exc)

    def make_folder(self, tv):  # Should scan folder first, movie_list should not be empty
        self.status = "Moving " + str(tv)

        try:
            if not os.path.isdir(self.work_folder):
                os.mkdir(self.work_folder)

        except Exception as exc:
            print(traceback.format_exc())
            print(exc)
            self.status = "Problem working with folder"
            print(self.status)
            return

        try:
            self.cut_episode(tv)

        except Exception as exc:
            print(traceback.format_exc())
            print(exc)
            self.status = "Problem Writing the File"
            print(self.status)

    def cut_episode(self, tv):
        paste = ""
        if not os.path.isdir(os.path.join(self.work_folder, tv.name)):
            os.mkdir(os.path.join(self.work_folder, tv.name))

        if tv.season is not None:
            if not os.path.isdir(os.path.join(self.work_folder, tv.name, "Season " + tv.season)):
                os.mkdir(os.path.join(self.work_folder, tv.name, "Season " + tv.season))
            if not os.path.isdir(os.path.join(self.work_folder, tv.name, "Season " + tv.season,
                                                "Episode " + tv.episode)):
                os.mkdir(os.path.join(self.work_folder, tv.name, "Season " + tv.season, "Episode " + tv.episode))

            paste = os.path.join(self.work_folder, tv.name, "Season " + tv.season, "Episode " + tv.episode,
                                 os.path.basename(tv.abspath))
        else:
            if not os.path.isdir(os.path.join(self.work_folder, tv.name, "Episode " + tv.episode)):
                os.mkdir(os.path.join(self.work_folder, tv.name, "Episode " + tv.episode))
            paste = os.path.join(self.work_folder, tv.name,
                                 "Episode " + tv.episode, os.path.basename(tv.abspath))
        if(paste != ""):
            os.rename(tv.abspath, paste)

    def icon_thread(self, folder, item):
        search = tmdb.Search()
        print("Setting icon for " +  os.path.join(folder, item))
        search.tv(query=item)
        poster_path = search.results[0]['poster_path']

        url = urllib.request.urlopen("https://image.tmdb.org/t/p/w200/" + poster_path)
        im = Image.open(url).convert('RGBA')
        im_new = Icon.expand2square(im)
        im_new.save(os.path.join(folder, item, "icon.ico"))
        os.system("attrib +H \"" + os.path.join(folder, item, "icon.ico\""))
        Icon.set_icon(os.path.join(folder, item), None)
    
    def set_icons(self, folder):
        listd = os.listdir(folder)
        for item in listd:
            if os.path.isfile(os.path.join(folder, item, "icon.ico")):
                continue

            try:
                t = threading.Thread(target=self.icon_thread, args=(folder, item))
                self.threads.append(t)
                t.start()

            except Exception as exc:
                print(traceback.format_exc())
                print(exc)
