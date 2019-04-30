
# coding: utf-8
# Autor: Fabiano Bernardi

__version__ = '1.0'

# import datetime
import pydicom
import json
import os
import shutil
import sys
import time

from pydicom import errors as dicomerror

file_count = 0
folder_count = -1
file_modal_count = 0
file_moved_count = 0


def get_json_conf():
    """
    Reads the JSON configuration file.
    It should be in the same folder as the script.
    """
    pwd = os.getcwd()
    os.chdir(pwd)
    # json_data = {}
    with open('config.json', 'r') as json_file:
        json_data = json.load(json_file)
    return json_data


def get_modality(config_file):
    """
    Gets the list of modalities to be searched.
    Return None if the search is by date only.
    :param config_file:
    :return:
    """
    if not config_file['StudyInfo']['Modality']:
        return None
    else:
        return config_file['StudyInfo']['Modality']


def get_study_range_dates(config_file):
    """
    Gets the start date and end date
    :param config_file:
    :return:
    """
    start_date = config_file['StudyInfo']['StudyDates']['StartDate']
    end_date = config_file['StudyInfo']['StudyDates']['EndDate']
    if not start_date:
        start_date = 19700101
    if not end_date:
        end_date = 20990101
    return int(start_date), int(end_date)


def get_work_folders(config_file):
    """
    Gets the source and destination folder.
    :param config_file:
    :return:
    """
    source_folder = config_file['Folders']['source']
    dest_folder = config_file['Folders']['destination']
    if not os.path.exists(source_folder):
        print('Pasta de origem não encontrada.')
        sys.exit()
    if not os.path.exists(dest_folder):
        create_dest_folder(dest_folder)
    return source_folder, dest_folder


def create_dest_folder(abs_path):
    """
    Create destination folder, if not exists.
    :param abs_path:
    :return:
    """
    try:
        os.makedirs(abs_path)
    except OSError as err:
        print('Erro na criação da pasta de destino. Veja mensagem de erro.')
        print(err)
        sys.exit()


def count_files(root_folder):
    """
    Count files in source folder.
    :param root_folder:
    :return:
    """
    file_counter = 0
    for root, dirs, files in os.walk(root_folder):
        for _ in files:
            file_counter += 1
    print('Total de arquivos na busca: {}'.format(file_counter))
    return file_counter


def test_modality(file, modalities):
    """
    Check if the image modality is in the search list
    :param modalities:
    :param file:
    :return:
    """
    if not file or not modalities:
        return False
    for modality in modalities:
        if file.Modality == modality:
            return True
    else:
        return False


def test_studydate(file, start_date, end_date):
    """Testa se a data da imagem está no intervalo definido para
    a pesquisa.
    """
    if not file:
        return False
    if start_date <= int(file.StudyDate) <= end_date:
        return True
    else:
        return False


def show_runtime(start, end):
    """Retorna o tempo total de execução do script."""
    # total_sec = end - start
    print('Tempo total de execução = {}'.format(
        time.strftime("%Hh%Mm%Ss", time.gmtime(end - start))))


def check_searching_filters(config):
    search_modalities = get_modality(config)
    start_date, end_date = get_study_range_dates(config)
    if not search_modalities and not start_date and not end_date:
        print('Nenhum filtro de busca definido.')
        sys.exit(0)
    if not search_modalities:
        print('Sem identificação de modalidade. A busca será por range de '
              'data das imagens.')
    if not start_date and not end_date:
        print('Sem range de data definido. A busca será apenas pela '
              'modalidade do exame.')


def retrieve_file(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            yield os.path.join(root, file)
    yield False


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1,
                       length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent
                                  complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    Source:
    https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    """
    percent = ("{0:." + str(decimals) + "f}").format(
        100 * (iteration / float(total))
    )
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


def get_dicom_file(dicom_file):
    try:
        file = pydicom.read_file(dicom_file)
        return file
    except dicomerror.InvalidDicomError:
        pass


def copy_file_to_dest(file_path, destination):
    try:
        shutil.copy(file_path, destination)
        # shutil.move(file, dst_path)
        return True
    except shutil.Error:
        return False


def worker(config, total):
    search_modalities = get_modality(config)
    start_date, end_date = get_study_range_dates(config)
    source_dir, dest_dir = get_work_folders(config)
    count = 1
    total_files_copied = 0
    files_copied = []
    files_not_copied = []
    for file in retrieve_file(source_dir):
        if not file:
            break
        dicom_file = get_dicom_file(os.path.join(source_dir, file))
        modality_ok = test_modality(dicom_file, search_modalities)
        imagedate_ok = test_studydate(dicom_file, start_date, end_date)
        if modality_ok and imagedate_ok:
            file_copied = copy_file_to_dest(os.path.join(source_dir, file),
                                            dest_dir)
            if file_copied:
                files_copied.append(os.path.join(source_dir, file))
                total_files_copied += 1
            else:
                files_not_copied.append(os.path.join(source_dir, file))
        print_progress_bar(count, total, 'Progresso:', 'de arquivos '
                                                       'verificados')
        count += 1
    print('Total de arquivos copiados: {}'.format(len(files_copied)))
    print('Total de arquivos não copiados: {}'.format(len(files_not_copied)))


def run():
    time_start = time.time()
    config = get_json_conf()
    check_searching_filters(config)
    source_dir, dest_dir = get_work_folders(config)
    total_files = count_files(source_dir)
    worker(config, total_files)
    time_end = time.time()
    print('Hora de início: {}'.format(time.strftime("%Hh%Mm%Ss", time.gmtime(
        time_start))))
    print('Hora de término: {}'.format(time.strftime("%Hh%Mm%Ss", time.gmtime(
        time_end))))


if __name__ == '__main__':
    run()
