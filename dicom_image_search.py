# coding: utf-8


# Autor: Fabiano Bernardi
# dicom_image_search.py

__version__ = '1.0'

import datetime
import pydicom
import json
import os
import shutil
import sys
import time

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
    return start_date, end_date


def get_start_studydate(dictionary):
    '''Retorna a data inicial das imagens a serem pesquisadas.
    A data é convertida para um int para facilitar a verificação.
    Se não foi fornecida a data inicial então retorna 0 (zero)
    como valor inicial da data.
    '''
    if (dictionary['StudyInfo']['StudyDate'][0] != ''):
        return int(dictionary['StudyInfo']['StudyDate'][0])
    else:
        return 0


def get_end_studydate(dictionary):
    '''Retorna a data final das imagens a serem pesquisadas.
    A data é convertida para um int para facilitar a verificação.
    Se não foi fornecida a data final então retorna o valor 30000101
    como valor final da data, que significa data = 01/01/3000.
    '''
    if (dictionary['StudyInfo']['StudyDate'][1] != ''):
        return int(dictionary['StudyInfo']['StudyDate'][1])
    else:
        return 30000101


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


def get_source_folder(dictionary):
    '''Retorna a pasta raiz onde a pesquisa deve ser realizada.'''
    folder = dictionary['Folders']['source']
    folder = os.path.normpath(folder)
    if (not folder.endswith(os.sep)):
        return folder + os.sep
    else:
        return folder


def get_destination_folder(dictionary):
    '''Retorna a pasta de destino para onde as imagens que atendem aos
    requisitos devem ser copiadas.
    '''
    folder = dictionary['Folders']['destination']
    folder = os.path.normpath(folder)
    if not folder.endswith(os.sep):
        return folder + os.sep
    else:
        return folder


def test_modality(file, modality):
    '''Testa se a modalidade da imagem é igual a modalidade
    a ser pesquisada.
    '''
    if file.Modality == modality:
        return True
    else:
        return False


def test_studydate(file, start_date, end_date):
    '''Testa se a data da imagem está no intervalo definido para
    a pesquisa.
    '''
    if (int(file.StudyDate) >= start_date and int(file.StudyDate) <= end_date):
        return True
    else:
        return False


def show_runtime(start, end):
    '''Retorna o tempo total de execução do script.'''
    total_sec = end - start
    print('Tempo total de execução = {}'.format(time.strftime("%Hh%Mm%Ss", time.gmtime(end - start))))


def check_dst_folder(dst):
    '''Verifica se a pasta existe e tenta criar caso seja necessário.'''
    if (not os.path.exists(os.path.normpath(dst))):
        try:
            os.makedirs(dst)
        except OSError:
            print('{}   Impossível criar pasta de destino: [{}]'.format(str(datetime.datetime.now()), dst))
            print('{}   Abortando execução do script.'.format(str(datetime.datetime.now())))
            sys.exit()


def searching_files(dictionary):
    '''Percorre a pasta raiz lendo arquivos que sejam DICOM e que se enquadrem nos
    parametros definidos para a busca. Se o arquivo é compatível o caminho absoluto
    será adicionado numa lista de arquivos a serem copiados.
    '''
    global folder_count
    global file_count
    global file_modal_count
    modality = get_modality(dictionary)
    start_date = get_start_studydate(dictionary)
    end_date = get_end_studydate(dictionary)
    root_folder = get_source_folder(dictionary)
    file_ok = False
    files_to_copy = []

    for root, dirs, files in os.walk(root_folder):
        print('{}   Procurando na pasta: {}'.format(str(datetime.datetime.now()), root))
        folder_count += 1
        for file in files:
            file_count += 1
            abs_path = root + os.sep + file
            try:
                df = dicom.read_file(abs_path)
            except dicom.errors.InvalidDicomError:
                print('Arquivo [{}] não é DICOM.'.format(abs_path))
            else:
                file_ok = (test_modality(df, modality)) and (test_studydate(df, start_date, end_date))
                # file_ok = test_studydate(df, start_date, end_date)
                if file_ok:
                    file_modal_count += 1
                    files_to_copy.append(abs_path)
    print('{}   Pesquisa por imagens finalizada.'.format(str(datetime.datetime.now())))
    return files_to_copy


def copy_files(dictionary, files_to_copy):
    '''Copia para a pasta de destino os arquivos compativeis encontrados na pesquisa.
    Os arquivos são copiados, mantendo o original na pasta de origem.
    '''
    global file_moved_count
    destination_folder = get_destination_folder(dictionary)
    root_folder = get_source_folder(dictionary)

    print('{}   Iniciando cópia dos arquivos para a pasta destino.'.format(str(datetime.datetime.now())))
    check_dst_folder(destination_folder)
    for file in files_to_copy:
        after_source = file.split(root_folder)[1]
        before_file = after_source.split(os.path.basename(after_source))[0]
        dst_path = destination_folder + os.sep + before_file
        check_dst_folder(dst_path)
        try:
            shutil.copy(file, dst_path)
            # shutil.move(file, dst_path)
            file_moved_count += 1
        except shutil.Error:
            print('Arquivo [{}] não foi copiado.'.format(file))
    print('{}   Arquivos de imagem copiados.\n'.format(str(datetime.datetime.now())))


def check_searching_filters(search_modalities, start_date, end_date):
    if not search_modalities and not start_date and not end_date:
        print('Nenhum filtro de busca definido.')
        sys.exit(0)
    if not search_modalities:
        print('Sem identificação de modalidade. A busca será por range de '
              'datas das imagens.')
    if not start_date and not end_date:
        print('Sem range de data definido. A busca será apenas pela '
              'modalidade do exame.')


def retrieve_file(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            yield os.path.join(folder_path, file)
    yield False


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1,
                     length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    Source:
    https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    """
    percent = ("{0:." + str(decimals) + "f}").format(
        100 * (iteration / float(total))
    )
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


def worker(config, total):
    search_modalities = get_modality(config)
    start_date, end_date = get_study_range_dates(config)
    source_dir, dest_dir = get_work_folders(config)
    count = 0
    for file in retrieve_file(source_dir):
        # print(count)
        # verificar modalidade
        # verificar data
        # se OK mover para destino
        printProgressBar(count, total, 'Progresso:', 'concluído')
        count += 1
        pass
    print(count)


def check_configuration(config):
    search_modalities = get_modality(config)
    start_date, end_date = get_study_range_dates(config)
    check_searching_filters(search_modalities, start_date, end_date)


def run():
    # time_start = time.time()
    config = get_json_conf()
    check_configuration(config)
    source_dir, dest_dir = get_work_folders(config)
    total_files = count_files(source_dir)
    worker(config, total_files)


if __name__ == '__main__':
    run()
    """files_to_copy = searching_files(dictionary)
    copy_files(dictionary, files_to_copy)

    print('Foram encontrados [{}] arquivos em [{}] pastas'.format(str(file_count), str(folder_count)))
    print('De [{}] arquivos lidos, foram encontrados [{}] arquivos de imagem a serem copiados'.format \
              (str(file_count), str(file_modal_count)))
    print('Total de arquivos de imagem copiados: [{}]'.format(str(file_moved_count)))
    time_end = time.time()
    print('Tempo total de execução = ' + time.strftime("%Hh%Mm%Ss", time.gmtime(time_end - time_start)))
"""