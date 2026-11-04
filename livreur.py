import asyncio
import spade
from agents.annuaire_agent import AnnuaireAgent
from agents.dispatcher_agent import DispatcherAgent
from agents.livreur_agent import LivreurAgent

async def main():
    annuaire = AnnuaireAgent("annuaire@localhost", "mdp")
    await annuaire.start(auto_register=True)

    livreurs = []
    for uid in (1, 2, 3):   # ids existants dans la table livreur
        l = LivreurAgent(f"livreur_{uid}@localhost", "mdp", utilisateur_id=uid)
        await l.start(auto_register=True)
        livreurs.append(l)

    await asyncio.sleep(2)  # laisser les livreurs s'enregistrer avant le dispatcher

    dispatcher = DispatcherAgent("dispatcher@localhost", "mdp")
    await dispatcher.start(auto_register=True)

    await spade.wait_until_finished(dispatcher)

spade.run(main())