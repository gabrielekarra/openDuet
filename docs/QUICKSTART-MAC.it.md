# OpenDuet sul tuo Mac

Questa guida installa la release candidate **0.4.0rc1**. Il Mac deve restare
acceso, sveglio e con la sessione utente aperta per ricevere richieste da remoto.

Installa [uv](https://docs.astral.sh/uv/getting-started/installation/). Su un Mac
con chip Apple Silicon esegui:

```sh
uv tool install --python 3.12 'openduet[mac,mlx] @ https://github.com/gabrielekarra/openDuet/releases/download/v0.4.0rc1/openduet-0.4.0rc1-py3-none-any.whl'
openduet setup --background --open
```

Su un Mac Intel sostituisci `openduet[mac,mlx]` con `openduet[mac,kev]`.
Il servizio parte anche ai successivi accessi a macOS. La configurazione, i dati
e le credenziali restano in `~/Library/Application Support/OpenDuet`.
Il browser si apre con un accesso locale monouso, valido due minuti.

1. Installa [Ollama](https://ollama.com/download) ed esegui
   `ollama pull qwen3.5:4b`, oppure scegli il tuo modello locale o un'API in
   **Impostazioni**. Premi **Verifica connessione**: viene verificata anche una
   chiamata a uno strumento innocuo. Il profilo iniziale usa Ollama nativo,
   contesto di 16.384 token e risposte fino a 2.048 token.
2. Nella pagina **Telegram**, crea un bot con BotFather, inserisci il suo token
   e apri il collegamento di abbinamento dal tuo account privato. Solo
   l'account abbinato può usare il bot. Non pubblicare il token.
3. Abilita l'accesso al Mac in **Impostazioni**. In **Impostazioni di sistema →
   Privacy e sicurezza**, concedi **Accessibilità** e **Registrazione schermo**
   all'eseguibile Python del servizio. Controlla il suo percorso con
   `openduet doctor`. Riavvia il servizio dopo aver concesso i permessi.
4. Su Telegram prova `/apps`, `/screen` e “Apri Calcolatrice”. Per le
   interazioni approva l'azione proposta. Gli screenshot vengono inviati come
   immagini; non viene aperta una sessione di condivisione dello schermo.
5. Per la proattività, scarica esplicitamente il modello Kev dalla relativa
   pagina e collega le fonti da controllare. La posta può essere collegata
   direttamente con una password per app; l'invio è facoltativo e approvato.
   Senza Kev puoi comunque assegnare lavori e ottenere riepiloghi.

```sh
openduet open                  # Apre un nuovo accesso locale monouso
openduet doctor                # Diagnostica e permessi, senza credenziali
openduet doctor --check-model  # Verifica anche modello e strumenti
openduet service status
openduet service stop
openduet service start
openduet service uninstall     # Rimuove i servizi, conserva i dati
```

Per aggiornare: salva una copia dell'installazione, ferma i servizi e usa il
comando di installazione della nuova release aggiungendo `--force`. Poi esegui
nuovamente `openduet setup --background --open`. Database, chiave della cassaforte,
allegati e documenti devono essere conservati insieme nel backup.

I [risultati delle prove](VALIDATION.md) distinguono i controlli automatici dalle
prove che richiedono il tuo Mac, il tuo bot e i tuoi account reali.
