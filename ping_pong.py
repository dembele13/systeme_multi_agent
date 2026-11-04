import time
from agents.annuaire_agent import AnnuaireAgent
from asyncio import run
import logging



logging.basicConfig(level=logging.DEBUG)

async def main():
    # Remplace par les identifiants de ton serveur XMPP local (ex: Prosody ou ejabberd)
    # JID format : nom_agent@domaine_ou_localhost
    jid = "admin@localhost"
    password = "2003"

    annuaire = AnnuaireAgent(jid, password)
    
    # Démarrage de l'agent
    await annuaire.start(auto_register=True)
    print("Agent Annuaire en cours d'exécution. Appuyez sur Ctrl+C pour quitter.")

    # Maintenir l'agent actif
    while annuaire.is_alive():
        await asyncio.sleep(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())