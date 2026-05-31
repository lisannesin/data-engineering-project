# Edenemisraport

> **Juhend:** See fail on projektitöö teise nädala väljund. Uuenda lühidalt iga esitamise eel. Kustuta see juhendrida.

## Mis on valmis

- [x] Docker Compose käivitab kõik teenused
- [x] Andmeid saadakse allikast kätte
- [x] Andmed laetakse `staging` kihti
- [x] Vähemalt üks transformatsioon toimib
- [x] Vähemalt üks näidikulaud on nähtaval
- [ ] Vähemalt üks andmekvaliteedi test läbib

Valmis on esmane andmevoog, mis tõmbab toodete andmed WooCommerce API-st PostgreSQL andmebaasi. Andmed salvestatakse RAW, STG ja MART kihtidesse. MART kihist loeb andmeid Streamlit dashboard, mis kuvab toodete koguarvu, laoseisu staatust ning toodete ülevaadet. Kogu lahendus töötab Docker Compose keskkonnas.

## Järgmised sammud

- Lisada andmekvaliteedi testid
- Lisada Synology Excleid sisendiks
- Graafikuid lisada juurde

## Mis takistab

-  Praegu pole blokeerivaid probleeme

## Kontrollpunkt

Käsk, millega saab kontrollida, et töövoog töötab:

```bash
# Näiteks:
docker compose up --build
```

Oodatav tulemus:

- PostgreSQL andmebaas käivitub edukalt
- WooCommerce API-st laetakse toodete andmed
RAW, STG ja MART kihid täidetakse andmetega
- Streamlit dashboard avaneb aadressil http://localhost:8501
