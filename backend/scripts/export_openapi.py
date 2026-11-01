import json
from bootstrap import ROOT
from app.main import app

if __name__ == "__main__":
    path = ROOT / "docs" / "openapi.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
    print("OpenAPI сохранён.")
