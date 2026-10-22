# Accesso remoto al computer

OpenDuet permette di vedere e controllare il computer da un altro PC, tablet o
telefono. La scheda **Computers / Computer** apre il desktop in una finestra del
browser: prima in sola visualizzazione, poi con **Take control / Prendi il controllo**
per usare mouse, touch e tastiera. Non serve un client desktop aggiuntivo sul
dispositivo da cui ti colleghi.

Il computer deve essere acceso e raggiungibile. OpenDuet non accende un PC spento,
non supera la schermata di blocco e non abilita da solo permessi amministrativi.

## Configurazione sul Mac con l'app OpenDuet

1. In macOS, abilita **Impostazioni di Sistema → Generali → Condivisione →
   Condivisione schermo**. Configura l'accesso consentito e, se necessario per il
   tuo server, la compatibilità VNC con una password dedicata. Usa le opzioni e
   i permessi del sistema, senza esporre la porta VNC su Internet. Le istruzioni
   Apple sul [controllo VNC](https://support.apple.com/it-it/guide/remote-desktop/apde0dd523e/mac)
   spiegano la configurazione e le differenze rispetto a Remote Desktop.
2. In **OpenDuet → Settings / Impostazioni → General / Generali**, abilita
   **Enable remote desktop access while OpenDuet is running / Abilita il desktop
   remoto mentre OpenDuet è attivo**.
3. Scegli **Copy workspace access token / Copia il token di accesso**. Il token
   viene generato casualmente e conservato nel Portachiavi del Mac. Ti servirà
   per accedere al workspace dall'altro dispositivo.
4. Apri `http://127.0.0.1:8765` sul Mac per verificare il workspace. Per accedere
   dall'esterno, configura una rete privata o un reverse proxy HTTPS come sotto.
5. Dall'altro dispositivo, accedi al workspace, apri **Computers → My Mac →
   Open desktop** e inserisci le credenziali richieste dal servizio di condivisione
   schermo. Scegli **Take control** quando vuoi usare il computer.

Il servizio remoto parte con l'app quando l'opzione è abilitata. Si arresta quando
disabiliti l'opzione o chiudi OpenDuet; controlla anche la vita del processo padre
per terminare dopo un'uscita forzata dell'app. Mantiene il Mac sveglio tramite
`caffeinate -i` mentre è attivo, senza cambiare permanentemente le impostazioni
di risparmio energetico. Il coperchio chiuso, uno stop esplicito, lo spegnimento,
la batteria esaurita o una rete non disponibile possono interrompere l'accesso.

La configurazione iniziale è in
`~/Library/Application Support/Bobb/Remote/openduet.toml`. Il percorso mantiene
il vecchio nome per compatibilità. Il comando **Show remote configuration** lo
mostra nel Finder. Il servizio gestito dall'app usa il suo workspace; non usa
automaticamente memoria o account del daemon locale. La condivisione desktop
funziona indipendentemente dalla disponibilità di un LLM.

## Collegamento dall'esterno

Un modo pratico è usare Tailscale su entrambi i dispositivi, nella tua rete
privata. Dopo averlo installato e collegato al tuo account, esegui **sul Mac**:

```sh
tailscale serve --bg http://127.0.0.1:8765
tailscale serve status
```

Apri dall'altro dispositivo l'indirizzo HTTPS mostrato dal comando. Il workspace
richiede comunque il suo token. [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
pubblica il servizio nella rete privata Tailscale; **Funnel** è invece una modalità
pubblica distinta e non è richiesta da OpenDuet. Puoi usare anche un altro VPN
o reverse proxy HTTPS di tua scelta.

Il proxy deve mantenere il nome host originale e inoltrare gli upgrade WebSocket
del percorso `/api/computers/<id>/desktop`. Configura i trusted proxy di Uvicorn
solo per il proxy che controlli. Con il servizio nativo sulla porta di loopback,
il proxy locale viene riconosciuto dalle impostazioni standard di Uvicorn.
Non inoltrare su Internet le porte VNC, né usare port forwarding pubblico per 5900.

Se hai già un workspace separato sulla porta 8765, usa quello configurando il
computer come sotto, oppure scegli una porta differente nel file del servizio
gestito dall'app. Non avviare due servizi sulla stessa porta.

## Configurazione manuale per PC, Linux o computer dell'agente

Avvia OpenDuet sul computer, oppure su un server che possa raggiungere il desktop
attraverso un tunnel locale. Abilita un server VNC compatibile sul computer da
controllare e aggiungi al tuo `openduet.toml`:

```toml
[computers.host]
name = "Il mio computer"
host = "127.0.0.1"
port = 5900
# Solo quando il servizio gira sullo stesso Mac dell'app nativa:
screen_lock = "~/Library/Application Support/Bobb/screen.lock"
```

Puoi aggiungere più sezioni `[computers.<id>]`, ad esempio per il PC personale e
una VM dell'agente. È consentita una sessione desktop alla volta. Il client
usa VNC/RFB tramite [noVNC](https://novnc.com/noVNC/docs/API.html); RDP non è
implementato direttamente. Su Windows usa un server VNC compatibile, su Linux
scegli quello adatto alla tua sessione X11/Wayland e ai suoi permessi.

Per un computer separato, un tunnel SSH mantiene il tratto VNC in una connessione
cifrata e presenta una porta di loopback al workspace:

```sh
# Sul server dove gira il workspace, verso un computer che amministri:
ssh -N -L 5901:127.0.0.1:5900 utente@computer
```

```toml
[computers.agent]
name = "Computer dell'agente"
host = "127.0.0.1"
port = 5901
```

Per endpoint fuori loopback, il relay richiede `tls = true`, con certificato
valido e `ca_file` opzionale. Si tratta di TLS esterno al flusso RFB, per esempio
un tunnel TLS; non basta che il server pubblicizzi un metodo VNC di sicurezza TLS
negoziato internamente. Un tunnel SSH locale è la configurazione più semplice.
Il modello non può cambiare destinazioni, porte, certificati o configurazione.

Nel container, `127.0.0.1` è il container stesso. Il desktop non viene creato dal
container OpenDuet: configura un tunnel nel suo namespace di rete o un endpoint
TLS raggiungibile. Per controllare il computer fisico, il servizio eseguito
direttamente sul computer è l'installazione più semplice.

## Passaggio del controllo e privacy

- Aprendo una sessione, i nuovi task del workspace restano in coda; il task in
  corso viene fermato. Un effetto esterno con esito incerto richiede verifica,
  seguendo le normali regole del motore. Non viene ripetuto automaticamente.
- Sullo stesso Mac, il relay chiede all'app di cedere il desktop e acquisisce lo
  stesso lock usato dall'automazione. Il collegamento attende il rilascio prima
  di passare input. Se un'azione non termina entro l'attesa, la sessione fallisce
  senza condividere il controllo. L'inserimento automatico in Mail è sospeso.
- **Disconnect**, chiusura della finestra, logout, spegnimento del servizio o
  scadenza terminano la sessione e rilasciano il controllo. I task fermati non
  vengono ripresi automaticamente; quelli già in coda possono proseguire.
- Le sessioni richiedono un login al workspace e un'Origin corrispondente.
  Le credenziali del desktop vengono gestite da noVNC e dal server VNC. Pixel,
  tastiera e password non sono inseriti nella chat o inviati a un modello.
  Il relay inoltra byte e registra solo apertura/chiusura, senza registrare lo schermo.
- La durata massima predefinita è un'ora, configurabile con
  `remote_session_seconds` tra un minuto e otto ore. Non vengono creati URL
  contenenti token di accesso.

Il lock coordina le azioni desktop di OpenDuet sullo stesso host. Altri programmi
di automazione o agenti in una VM richiedono una propria integrazione con il lock;
il relay non può fermare software di terzi che non lo rispetta. Il browser
headless opzionale del workspace resta separato dal desktop: non diventa visibile
solo perché hai aperto lo schermo del computer.

## Verifica di questa implementazione

I test coprono autenticazione, Origin, disconnessione al logout/scadenza, sessione
esclusiva, relay binario, attesa del lock nativo e pausa della coda. Un test Chromium
esegue l'handshake RFB, riceve un framebuffer e invia mouse e tastiera attraverso
la UI e il WebSocket fino a un desktop sintetico locale.

Le autorizzazioni macOS e la compatibilità del server desktop scelto richiedono
una prova sul computer reale. Questa sessione di sviluppo non ha accesso al tuo
Mac e non abilita la condivisione schermo o la VPN al suo posto.
