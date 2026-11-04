from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from api.database import get_db_connection
from api.routers import admin, commandes, livreurs, offre, client, auth, communes

app = FastAPI(
    title="API Plateforme de Livraison SMA",
    version="2.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Indiquer à FastAPI où se trouvent les fichiers HTML
templates = Jinja2Templates(directory="templates")

# Inclusion des routers
app.include_router(auth.router)
app.include_router(client.router)
app.include_router(livreurs.router)
app.include_router(commandes.router)


app.include_router(communes.router)

# Route pour afficher la page d'authentification
@app.get("/login", response_class=HTMLResponse)
def afficher_page_auth(request: Request):
   return templates.TemplateResponse(request, "auth.html", {})
#affichage livreur 
@app.get("/client/dashboard", response_class=HTMLResponse)
def page_client(request: Request):
    return templates.TemplateResponse(request, "client_commandes.html")

@app.get("/livreur/dashboard", response_class=HTMLResponse)
def page_livreur(request: Request):
    return templates.TemplateResponse(request, "livreur_dashboard.html")

@app.get("/admin/dashboard", response_class=HTMLResponse)
def page_admin(request: Request):
    return templates.TemplateResponse(request, "admin_dashboard.html")

@app.get("/communes")
def get_communes():
    try:
        # Remplacez ceci par votre propre méthode de connexion à la BD
        conn = get_db_connection() 
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nom FROM commune ORDER BY nom ASC;")
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Transformation propre en liste de dictionnaires
        communes = [{"id": row[0], "nom": row[1]} for row in rows]
        return communes
        
    except Exception as e:
        # Cela va afficher l'erreur exacte directement sur la page web ou dans Postman
        print(f"ERREUR SQL / COMMUNES : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

@app.get("/")
def root():
    return {"message": "API de la plateforme de livraison urbaine opérationnelle active"}
