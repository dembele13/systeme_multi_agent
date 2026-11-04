CREATE TABLE IF NOT EXISTS commune (
    id   SERIAL PRIMARY KEY,
    nom  VARCHAR(50) NOT NULL UNIQUE,
    lat  DOUBLE PRECISION NOT NULL,
    lon  DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS utilisateur (
    id          SERIAL PRIMARY KEY,
    nom         TEXT NOT NULL,
    telephone   TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL CHECK (role IN ('client','livreur','admin')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS livreur (
    utilisateur_id INT PRIMARY KEY REFERENCES utilisateur(id),
    commune_id     INT REFERENCES commune(id),
    vehicule       TEXT NOT NULL CHECK (vehicule IN ('moto','voiture','velo')),
    capacite_kg    REAL NOT NULL,
    zone           TEXT NOT NULL DEFAULT 'centre',
    en_ligne       BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS commande (
    id              SERIAL PRIMARY KEY,
    client_id       INT NOT NULL REFERENCES utilisateur(id),
    livreur_id      INT REFERENCES livreur(utilisateur_id),
    statut          TEXT NOT NULL DEFAULT 'creee'
                    CHECK (statut IN ('creee','attribuee','livree','annulee','echec')),
    commune_depart_id INT NOT NULL REFERENCES commune(id),
    commune_arrivee_id INT NOT NULL REFERENCES commune(id),
  
    poids_kg        REAL NOT NULL,
    prix            INT NOT NULL,
    cree_le         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS offre ( 
    id            SERIAL PRIMARY KEY,
    commande_id   INT NOT NULL REFERENCES commande(id),
    livreur_id    INT NOT NULL REFERENCES livreur(utilisateur_id),
    cout_s        REAL, -- NULL si refus
    motif_refus   TEXT,
    retenue       BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS evaluation (
    id            SERIAL PRIMARY KEY,
    commande_id   INT NOT NULL REFERENCES commande(id),
    livreur_id    INT NOT NULL REFERENCES livreur(utilisateur_id),
    note          INT NOT NULL CHECK (note BETWEEN 0 AND 5),
    commentaire   TEXT
);
