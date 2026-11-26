import os
from fastapi.testclient import TestClient

def setup_module():
    import tempfile
    os.environ["OPENPROSPECT_HOME"]=tempfile.mkdtemp(prefix="openprospect-test-")

def test_database_and_dashboard():
    from openprospect.db import add_company,list_companies,add_contact,list_contacts,add_draft,list_drafts,set_draft_status
    ident=add_company("Example Cafe","https://example.test","Cafe","Test City")
    assert list_companies()[0]["name"]=="Example Cafe"
    add_contact(ident,"Alex","Owner","alex@example.test")
    assert list_contacts()[0]["company_name"]=="Example Cafe"
    draft=add_draft("Hello",company_id=ident,subject="Introduction")
    assert list_drafts()[0]["status"]=="draft"
    set_draft_status(draft,"approved")
    assert list_drafts()[0]["status"]=="approved"

def test_dashboard_and_company_api():
    from openprospect.app import app
    client=TestClient(app, base_url="http://127.0.0.1")
    from openprospect.security import get_dashboard_token
    assert client.get("/").status_code == 200  # unauthenticated users see sign-in
    login = client.post("/auth/exchange", json={"token": get_dashboard_token()})
    assert login.status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/train").status_code == 200
    response=client.post("/api/companies",json={"name":"API Business"})
    assert response.status_code==200
    assert response.json()["ok"] is True
    assert client.get("/api/companies").status_code==200

def test_suppression():
    from openprospect.db import add_suppression,is_suppressed
    add_suppression("stop@example.test")
    assert is_suppressed("stop@example.test")
