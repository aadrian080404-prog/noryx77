import json

from core.scientific_sources import ArxivSourceProvider, CrossrefSourceProvider, PubMedSourceProvider


def test_arxiv_adapter_parses_public_metadata_without_access_bypass(monkeypatch):
    xml = b'''<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1234.5678</id><title> Example Research </title><summary> An abstract. </summary></entry></feed>'''
    provider = ArxivSourceProvider()
    monkeypatch.setattr(provider, "_get", lambda url, accept: xml)
    sources = provider.search("example", max_results=1)
    assert len(sources) == 1
    assert sources[0].source_id == "arxiv:1234.5678"
    assert sources[0].access_status == "authorized"
    assert sources[0].content_digest


def test_crossref_adapter_parses_metadata_only(monkeypatch):
    payload = json.dumps({"message": {"items": [{"DOI": "10.1234/example", "title": ["Example Paper"]}]}}).encode()
    provider = CrossrefSourceProvider()
    monkeypatch.setattr(provider, "_get", lambda url, accept: payload)
    sources = provider.search("example", rows=1)
    assert len(sources) == 1
    assert sources[0].source_id == "crossref:10.1234/example"
    assert sources[0].access_status == "metadata_only"


def test_pubmed_adapter_requires_registered_contact_and_parses_ids(monkeypatch):
    provider = PubMedSourceProvider(email="research@example.org")
    responses = iter([
        json.dumps({"esearchresult": {"idlist": ["12345"]}}).encode(),
        json.dumps({"result": {"12345": {"title": "Example PubMed Record"}}}).encode(),
    ])
    monkeypatch.setattr(provider, "_get", lambda url, accept: next(responses))
    sources = provider.search("example", retmax=1)
    assert len(sources) == 1
    assert sources[0].source_id == "pubmed:12345"
    assert sources[0].access_status == "metadata_only"
