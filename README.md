### Descrizione

Semplice bot relizzato come progetto formativo utilizzando il framework [Rasa Open Source](https://rasa.com/).
È possibile:
- ordinare pizze
- vedere il menu
- chiedere ingredienti presenti su una pizza
- chiedere il prezzo di una pizza
- chiedere l'orario di apertura

Non occorrono comandi, il bot è in grado di elaborare il linguaggio naturale.
### Setup 
#### 1. Clonazione repository
```sh
git clone https://github.com/hidingbit/rasa-pizza-bot.git
cd rasa-pizza-bot
```
#### 2. Installazione di Python, pip e il modulo per creare virtual environment 
Per distribuzioni GNU/Linux Debian based con package manager **apt**:
```sh
sudo apt update
sudo apt install python3-dev python3-pip python3-venv
```
#### 3. Creazione ed attivazione del virtual environment
```sh
python3 -m venv ./venv
source ./venv/bin/activate

deactivate  #per disattivare
```
#### 4. Aggiornare pip e installare i requirements
```sh
pip3 install -U pip
python3 -m pip install -r requirements.txt
```
#### 5. Training
**NOTA**: occorre aver abilitato il virtual environment creato al punto 3.
```sh
rasa train
```
#### 6. Avvio
```sh
rasa run
```
oppure per provare il bot via shell:
```sh
rasa shell
```