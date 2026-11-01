"""Export the same original documents and feature list that the site displays."""
from bootstrap import ROOT
from app.services.consent import public_bundle

if __name__ == "__main__":
    bundle = public_bundle()
    directory = ROOT / "docs" / "agreements"
    directory.mkdir(parents=True, exist_ok=True)
    header = "B bank · учебный проект\n\n" + bundle['organizer'] + "\n\nРедакция: " + bundle['date'] + "\n\nВерсия: " + bundle['version'] + "\n\n"
    all_documents = []
    for document in bundle['documents']:
        body = "# " + document['title'] + "\n\n" + header + "\n\n".join("## " + section['title'] + "\n\n" + "\n\n".join(section['paragraphs']) for section in document['sections']) + "\n"
        (directory / (document['id'] + ".md")).write_text(body, encoding="utf-8")
        all_documents.append(body)
    (directory / "all-agreements.md").write_text("\n\n---\n\n".join(all_documents), encoding="utf-8")
    (ROOT / "docs" / "bank-functions.md").write_text("# Как работает B bank\n\n" + "\n\n".join("## " + item['title'] + "\n\n" + item['text'] + "\n\nРаздел: " + item['path'] for item in bundle['features']) + "\n", encoding="utf-8")
    print("Соглашения и перечень функций экспортированы в docs/.")
