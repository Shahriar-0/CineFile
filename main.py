import PySimpleGUI as sg 
import threading
import os
from cinefile import * 

sg.theme("Reddit")
working_thread = False

def collapse(layout, key, visible=False):
    return sg.pin(sg.Column(layout, key=key, visible=visible))

def thread(event, window):
    global working_thread
    if(event.endswith("-START") and working_thread):
        window['-ERR-'].update("Already Working...")
        return
    window.disappear()
    try:
        if(not check_connection()):
            print("Can't connect to the network")
            window.reappear()
            return

        working_thread = True
        if event == "MV-START":
            if r"{MOVIENAME}" not in values['pattern']:
                window['-ERR-'].update(r"Pattern should contain {MOVIENAME}")

            elif not os.path.isdir(values['MV-PATH']):
                window['-ERR-'].update(r" Folder Does Not Exist")
            
            else:
                mvscanner = MovieScanner(values['MV-PATH'])
                mvscanner.folder_pattern = values['pattern']
                mvscanner.rec_search = values['MV-RECURSIVE']
                mvscanner.scan_folder()
                
                for thread in mvscanner.threads:
                    thread.join()
                mvscanner.make_folders()
                
                if(values['MV-MOVICON']):
                    mvscanner.set_icons()
                    for thread in mvscanner.threads:
                        thread.join()

                if(values['MV-DIRICON']):
                    diricon = DirectorIcon(values['MV-PATH']  + os.path.sep + "CineFile")

                    diricon.scan_folder(mvscanner)
                    for thread in diricon.threads:
                        thread.join()

                    diricon.set_icons()
                    for thread in diricon.threads:
                        thread.join()
        
        elif event == "DIR-START":
            if not os.path.isdir(values['DIR-PATH']):
                window['-ERR-'].update(r" Folder Does Not Exist")
            else:
                    diricon = DirectorIcon(values['DIR-PATH'])
                    diricon.scan_folder()
                    for thread in diricon.threads:
                        thread.join()

                    diricon.set_icons()
                    for thread in diricon.threads:
                        thread.join()
        
        elif event == "SER-START":
            if not os.path.isdir(values['SER-PATH']):
                window['-ERR-'].update(r" Folder Does Not Exist")
            else:
                tv = TVScanner(values['SER-PATH'])
                tv.rec_search = values['SER-RECURSIVE']
                tv.scan_folder()
                
                if(values['SER-ICON']):
                    if(os.path.isdir(values['SER-PATH'] + os.path.sep + "CineFile - Series")):
                        tv.set_icons(values['SER-PATH'] + os.path.sep + "CineFile - Series") 
                        for thread in tv.threads:
                            thread.join()
        
        print("Done")
        window.reappear()
        working_thread = False
    except Exception as exc:
                print(traceback.format_exc())
                print(exc)
                window.reappear()
                working_thread = False

def clear_cache():

    layout = [[sg.Text('Clear windows icon caches and restart?')],
              [sg.Button("OK"), sg.Button("Cancel")]]

    window = sg.Window('Clear Cache', layout, icon="../icon.ico")
    while(True):
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            window.close()
            break
        elif event == "OK":
            Icon.clear_iconcache()
            os.system("shutdown /r /t 1")
        window.close()


menu_def = [['&Tools', ['&Clear Icon Caches']],
                ['&Help', '&About...'],]

movie_section = [[sg.Text("Folder names pattern: (e.g. 2011 - Melancholia)")], [sg.Input(default_text="{YEAR} - {MOVIENAME}",key="pattern")],
                [sg.Text("Choose a folder: ")], [sg.Input(key="MV-PATH"), sg.FolderBrowse()],
                [sg.CB("Download and set director icons", key="MV-DIRICON")],
                [sg.CB("Download and set movie icons", key="MV-MOVICON")],
                [sg.CB("Search all subfolders", key="MV-RECURSIVE")],
                [sg.Button("Start", key="MV-START")]
                ]

dir_section = [
                [sg.Text("Choose a folder: ")], [sg.Input(key="DIR-PATH"), sg.FolderBrowse()],
                [sg.Button("Start", key="DIR-START")]
                ]

series_section = [
                [sg.Text("Choose a folder: ")], [sg.Input(key="SER-PATH"), sg.FolderBrowse()],
                [sg.CB("Download and set Series Posters", key="SER-ICON")],
                [sg.CB("Search all subfolders", key="SER-RECURSIVE")],
                [sg.Button("Start", key="SER-START")]
                ]

radios = [[sg.Radio("Scan Movies", 1, key="RAD-MV", enable_events=True, default=True)] , [sg.Radio("Download Director Icons", 1 , key="RAD-DIR", enable_events=True)], [sg.Radio("Scan Series", 1, key="RAD-SER", enable_events=True)]]
error = [sg.T(text_color="red", size=(400,20), font=('Franklin Gothic Book', 10, 'bold'), key="-ERR-")]
layout = [[sg.Menu(menu_def, tearoff=False, pad=(20,1))], *radios, [sg.T("") for i in range(1,3)],[collapse(movie_section,"MV", visible=True), collapse(dir_section,"DIR") , collapse(series_section,"SER")], [sg.T("") for i in range(0,3)], error]
window = sg.Window("Cinefile", layout, icon="../icon.ico", size=(500, 500))

while(True):
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        window.close()
        break
    elif event.startswith("RAD-"):
        window['-ERR-'].update("")
        for n in ["MV", "DIR", "SER"]:
            window[n].update(visible = False)
        window[event[4:]].update(visible=True)
    elif event == "Clear Icon Caches":
        clear_cache()
    elif event == "About...":
        sg.popup('About this program','Version 1.0', 'Cinefile: Your Movie Archive Assistant', icon="../icon.ico", grab_anywhere=True)
    else:
        threading.Thread(target=thread, args=(event, window,), daemon=True).start()
        




