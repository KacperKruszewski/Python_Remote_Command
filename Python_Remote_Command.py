#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import threading
import paramiko
import atexit
import sys
from queue import Queue

site = 'your_site'

ssh_user = 'username'
ssh_password = 'password'

# Liczba wątków obsługujących kopie zapasowe
NUM_THREADS = 2  # Ustaw liczbę wątków na wartość 4 (możesz dostosować)

my_file = open("ip_device_list.txt")
ip_queue = Queue()

buff = ''
resp = ''

print(f"Lączenie do przełączników w lokalizacji {site}\n")

# Lista do przechowywania informacji o zakończonych kopii
remote_configuration = []

def IPokuyan():
    while True:
        IP = ip_queue.get()
        try:
            print(f"Logowanie do {IP} - rozpoczęcie zmiany konfiguracji urządzenia")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(IP, username=f'{ssh_user}', password=f'{ssh_password}')  # Zastąp rzeczywistą nazwą użytkownika i hasłem
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            chan = ssh.invoke_shell()
            chan.settimeout(15)

            # Wysyłanie poleceń do urządzenia
            chan.send('terminal length 0\n')
            time.sleep(1)
            chan.send('show clock\n')
            time.sleep(1)
            
            chan.send('configure terminal\n')
            time.sleep(1)
            chan.send('\r\n')
            time.sleep(1)
            chan.send('\r\n')
            time.sleep(1)
            
            buff = ''
            while buff.find('Building') < 0:
                resp = chan.recv(9999).decode('utf-8')
                buff += resp
                print(f"\nKonfiguracja zdalna zakończona dla urządzenia: {IP}")

            # Zamykanie połączenia SSH
            chan.send('end\n')  # Wysyłanie polecenia wyjścia
            time.sleep(1)
            chan.send('write\n')  # Wysyłanie polecenia wyjścia
            time.sleep(5)
            ssh.close()
            print(f"\nWylogowano z {IP}")
            
        except paramiko.ssh_exception.SSHException as ssh_error:
            print(f"\nBłąd SSH podczas zmiany konfiguracji urządzenia {IP}: {str(ssh_error)}")
            remote_configuration.append(IP) # Dodawanie IP urządzenia do listy niewykonanych kopii

        except Exception as e:
            print(f"Błąd podczas zmiany konfiguracji urządzenia {IP}: {str(e)}")
            remote_configuration.append(IP)
            
        finally:
            ip_queue.task_done()

def close_program():
    global program_close
    if not program_close:
        program_close = True
        print("Zamykanie programu...")
        my_file.close()

        # Sprawdzanie, czy wszystkie oczekiwane kopie zostały zakończone
        if len(remote_configuration) == ip_queue.qsize():
            print("Wszystkie konfiguracje zostały pomyślnie wykonane.")
        else:
            print("\nUwaga: Nie wszystkie konfiguracje zdalne zostały zakończone pomyślnie!")
            print("Niewykonane konfiguracje dla urządzeń: ")
            for device in remote_configuration:
                print(device)
                
        while True:
            answer = input("\nProgram można zakończyć poprzez naciśnięcie Ctrl+C").strip().lower()
            
if __name__ == "__main__":
    program_close = False
    
    for i in range(NUM_THREADS):
        t = threading.Thread(target=IPokuyan)
        t.daemon = True
        t.start()

    for line in my_file:
        l = [i.strip() for i in line.split()]
        IP = l[0]
        ip_queue.put(IP)

    atexit.register(close_program)  # Rejestrowanie funkcji do wywołania przy zamykaniu programu

    ip_queue.join()
    time.sleep(1)