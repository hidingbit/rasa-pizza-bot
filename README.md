# Rasa pizza-bot 🍕

Semplice bot realizzato come progetto formativo utilizzando il framework [Rasa Open Source](https://rasa.com/).

È possibile:
- ordinare pizze
- vedere il menu
- chiedere ingredienti presenti su una pizza
- chiedere il prezzo di una pizza
- chiedere l'orario di apertura

Non occorrono comandi, il bot è in grado di elaborare il linguaggio naturale.
## Setup 
### 1. Clonazione repository
```sh
git clone https://github.com/hidingbit/rasa-pizza-bot.git
cd rasa-pizza-bot
```
### 2. Installazione di Python, pip e il modulo per creare virtual environment 
Per distribuzioni GNU/Linux con package manager **apt**:
```sh
sudo apt update
sudo apt install python3-dev python3-pip python3-venv
```
### 3. Creazione ed attivazione del virtual environment
```sh
python3 -m venv .venv
source .venv/bin/activate

deactivate  # per disattivare
```
### 4. Aggiornamento pip ed installazione dei requirements
```sh
pip3 install -U pip
python3 -m pip install -r requirements.txt
```
### 5. Training
**Nota**: occorre aver abilitato il virtual environment creato al punto 3.
```sh
rasa train
```
### 6. Avvio del server
```sh
rasa run # Di default in ascolto sulla porta 5005.

# Oppure, se si vuole specificare un numero di porta diverso da quello di default
rasa run -p 4004 # Server in ascolto sulla porta 4004.
```
### 7. Avvio di Rasa Action Server
Da avviare su un nuovo terminale.
Necessario per l'esecuzione delle Custom Actions e validazione form.
```sh
rasa run actions
```
### 8. Avvio di Duckling
**Nota**: Occorre aver installato [Docker Engine](https://docs.docker.com/engine/install/).
```sh
docker run -p 8000:8000 rasa/duckling

# Se l'utente non appartiene al gruppo docker occorrono privilegi di amministratore.
sudo docker run -p 8000:8000 rasa/duckling
```
Se si vuole specificare un numero di porta diverso da 8000 su cui porre in ascolto Duckling, occorre modificare di conseguenza anche il file **config.yml** in questa sezione:
```yaml
- name: DucklingEntityExtractor
  url: "http://localhost:<NUMERO_PORTA>"
  dimensions: ["number"]
  locale: "it_IT"
```
### Per provare il bot via shell:
```sh
rasa shell
```
