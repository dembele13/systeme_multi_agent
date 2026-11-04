from agents.dispatcher_agent import selectionner_livreurs_eligibles

# Commande à Koumassi, 10 kg
CMD = {"poids_kg": 10, "emplacement_lat": 5.299, "emplacement_lon": -3.945}

def liv(id, cap, lat, lon):
    return {"id": id, "capacite_kg": cap, "lat": lat, "lon": lon}

def test_capacite_insuffisante_exclu():
    # Tout près, mais 5 kg < 10 kg
    assert selectionner_livreurs_eligibles([liv(1, 5, 5.300, -3.946)], CMD) == []

def test_trop_loin_exclu():
    # Yopougon, environ 15 km
    assert selectionner_livreurs_eligibles([liv(2, 50, 5.340, -4.087)], CMD) == []

def test_position_inconnue_exclu():
    assert selectionner_livreurs_eligibles([liv(3, 50, None, None)], CMD) == []

def test_tri_par_distance():
    livreurs = [
        liv(10, 20, 5.304, -3.983),  # Marcory, environ 4 km
        liv(11, 20, 5.301, -3.950),  # tout près
    ]
    res = selectionner_livreurs_eligibles(livreurs, CMD)
    assert [l["id"] for l in res] == [11, 10]

def test_valeurs_en_chaine():
    # Cas Decimal converti en str par json
    res = selectionner_livreurs_eligibles([liv(4, "20.0", "5.301", "-3.950")], CMD)
    assert len(res) == 1

