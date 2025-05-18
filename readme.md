# Выпускная квалификационная работа
## Тема: Разработка desktop-приложения для сбора и хранения научных данных по учёту и регистрации животных (на примере «North Pacific Wildlife Consulting LLC»)
# PhotoCount
## North Pacific Wildlife Consulting LLC
### Steller sea lion project

## Установка

1. Клонировать этот репозиторий
2. Установить зависимости
    ```bash
    pip install -r requirements.txt
    ```

## Создать пользовательский интерфейс из макета
Команда конвертирует описание интерфейса пользователя из файла .ui в исполняемый Python код и записывает его в файл .py
   ```bash
   pyuic5 ui_design/window_main.ui -o app/view/ui_window_main.py
   pyuic5 ui_design/window_location.ui -o app/view/ui_window_location.py
   pyuic5 ui_design/window_count.ui -o app/view/ui_window_count.py
   pyuic5 ui_design/window_count_report.ui -o app/view/ui_window_count_report.py
   pyuic5 ui_design/window_animal_registration.ui -o app/view/ui_window_animal_registration.py
   pyuic5 ui_design/window_animal_id.ui -o app/view/ui_window_animal_id.py
   pyuic5 ui_design/window_animal_id_report.ui -o app/view/ui_window_animal_id_report.py
   pyuic5 ui_design/dialog_location.ui -o app/view/ui_dialog_location.py
   pyuic5 ui_design/dialog_visual_count.ui -o app/view/ui_dialog_visual_count.py
   pyuic5 ui_design/dialog_create_count.ui -o app/view/ui_dialog_create_count.py
   pyuic5 ui_design/dialog_add_effort.ui -o app/view/ui_dialog_add_effort.py
   pyuic5 ui_design/dialog_add_count_photos.ui -o app/view/ui_dialog_add_count_photos.py
   pyuic5 ui_design/form_sub_count.ui -o app/view/ui_form_sub_count.py
   ```

## Локализация интерфейса пользователя
1. Команда найдет все Python файлы в каталоге app/view и его подкаталогах, а затем применит команду pylupdate5 
к каждому найденному файлу, создавая .ts файл для каждого из них с тем же базовым именем в каталог translates/Russian/.

    ```bash
    Get-ChildItem -Path app/view -Recurse -Include "*.py" | ForEach-Object { pylupdate5 $_.FullName -ts "translates/Russian/$($_.BaseName).ts" }
    ```
2. Команда преобразует указанные файлы .ts в файлы перевода ru.qm с готовым переводом.
    ```bash
    & "C:\Program Files (x86)\Qt Designer\lrelease.exe" ui_dialog_add_count_photos.ts ui_dialog_add_effort.ts ui_dialog_create_count.ts ui_dialog_location.ts ui_dialog_visual_count.ts ui_form_sub_count.ts ui_window_animal_id.ts ui_window_animal_id_report.ts ui_window_animal_registration.ts ui_window_count.ts ui_window_count_report.ts ui_window_location.ts ui_window_main.ts -qm ru.qm
    ```

## Собрать ресурсы
Команда преобразует файлы ресурсов .qrc в модуль python
```bash
pyrcc5 app/resources/resources.qrc -o resources_rc.py
```

## Собрать программу в один файл
Команда создает один исполняемый файл .exe
```bash
pyinstaller --name=PhotoCount --onefile --icon=app/resources/logo-pc.ico --noconsole app/windows/main.py --version-file=version.py
```

