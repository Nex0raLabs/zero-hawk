from mcp.server.fastmcp import FastMCP
from .db import list_companies, add_company
from .ai import ask_ai

mcp=FastMCP('Zero Hawk')

@mcp.tool()
def search_companies(limit:int=50)->list[dict]:
    """List companies stored in the local Zero Hawk database."""
    return list_companies(limit)

@mcp.tool()
def save_company(name:str,website:str='',industry:str='',location:str='',notes:str='')->dict:
    """Save a company prospect in Zero Hawk."""
    return {'id':add_company(name,website,industry,location,notes,source='mcp'),'saved':True}

@mcp.tool()
def ask_configured_ai(prompt:str)->str:
    """Send a prompt to the AI provider configured in Zero Hawk .env."""
    return ask_ai(prompt)

def main(): mcp.run()

if __name__=='__main__': main()
