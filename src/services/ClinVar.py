import re
import time
import httpx
from typing import List
from config.models.diseases import DiseaseInputModel
from config.models.variants import VariantInputModel

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

AA_THREE_TO_ONE = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    "Ter": "*",
}
AA_ONE_TO_THREE = {v: k for k, v in AA_THREE_TO_ONE.items()}


def search_by_disease(disease: str, limit: int = 20) -> List[str]:
    r = httpx.get(f"{EUTILS_BASE}/esearch.fcgi", params={
        "db": "clinvar",
        "term": f"{disease}[disease]",
        "retmax": limit,
        "retmode": "json"
    })
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    print(f"esearch returned IDs: {ids}")
    return ids


def fetch_summaries(ids: List[str]):
    if not ids:
        print("No IDs found.")
        return [], []

    print(f"Fetching summaries for {len(ids)} variation IDs...")
    r = httpx.get(f"{EUTILS_BASE}/esummary.fcgi", params={
        "db": "clinvar",
        "id": ",".join(ids),
        "retmode": "json"
    })

    if r.status_code == 429:
        print("Rate limited by NCBI — waiting 1s and retrying...")
        time.sleep(1)
        r = httpx.get(f"{EUTILS_BASE}/esummary.fcgi", params={
            "db": "clinvar",
            "id": ",".join(ids),
            "retmode": "json"
        })

    data = r.json().get("result", {})

    variants = []
    diseases = []

    for vid in data.get("uids", []):
        try:
            item = data[vid]
            obj_type = item.get("obj_type", "")
            if obj_type in ["copy number loss", "copy number gain", "Variation"]:
                continue

            germline = item.get("germline_classification", {})
            trait_set = germline.get("trait_set", [])
            disease_name = trait_set[0].get("trait_name") if trait_set else None
            medgen_id = None
            if trait_set:
                for ref in trait_set[0].get("trait_xrefs", []):
                    if ref.get("db_source") == "MedGen":
                        medgen_id = ref.get("db_id")
                        break

            if not disease_name or not medgen_id:
                continue
            if disease_name.lower() in ["not specified", "not provided", "see cases", "not applicable"]:
                continue

            diseases.append(DiseaseInputModel(tag=medgen_id, text=disease_name))

            consequence_list = item.get("molecular_consequence_list", [])
            consequence = consequence_list[0] if consequence_list else None
            variation_set = item.get("variation_set", [])
            xrefs = variation_set[0].get("variation_xrefs", []) if variation_set else []
            rsid = next((x.get("id") for x in xrefs if x.get("db", "").lower() == "dbsnp"), None)
            genes = item.get("genes", [])
            gene_symbol = genes[0].get("symbol") if len(genes) == 1 else None

            variants.append(VariantInputModel(
                tag=vid,
                title=item.get("title", ""),
                clinical_significance=germline.get("description"),
                consequence=consequence,
                rsid=rsid,
                gene_symbol=gene_symbol,
                disease_tag=medgen_id,
                protein_tag=None
            ))
        except Exception as e:
            print(f"Skipping variant {vid}: {e}")
            continue

    print(f"Received summaries for {len(variants)} variants.")
    return variants, diseases


def search_clinvar(disease: str, limit: int = 20):
    "Search ClinVar by disease name. Returns (variants, diseases)."
    ids = search_by_disease(disease, limit)
    return fetch_summaries(ids)


def _normalize_variant_input(raw: str) -> List[str]:
    raw = raw.strip()
    terms = [raw]

    m = re.match(r'^p?\.?([A-Z])(\d+)([A-Z*])$', raw)
    if m:
        ref1, pos, alt1 = m.groups()
        ref3 = AA_ONE_TO_THREE.get(ref1, ref1)
        alt3 = AA_ONE_TO_THREE.get(alt1, alt1)
        terms += [f"p.{ref1}{pos}{alt1}", f"{ref3}{pos}{alt3}", f"p.{ref3}{pos}{alt3}"]

    m3 = re.match(r'^p?\.?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|\*)$', raw)
    if m3:
        ref3, pos, alt3 = m3.groups()
        ref1 = AA_THREE_TO_ONE.get(ref3, ref3[0])
        alt1 = AA_THREE_TO_ONE.get(alt3, alt3[0])
        terms += [f"p.{ref3}{pos}{alt3}", f"{ref1}{pos}{alt1}", f"p.{ref1}{pos}{alt1}"]

    if re.match(r'^\d+[ACGT]>[ACGT]$', raw):
        terms.append(f"c.{raw}")

    return list(dict.fromkeys(terms))


def _title_matches(title: str, terms: List[str]) -> bool:
    title_lower = title.lower()
    for term in terms:
        t = term.lower()
        if t in title_lower:
            return True
        if f"({t})" in title_lower:
            return True
        if t.startswith("p.") and t[2:] in title_lower:
            return True
    return False


def lookup_variant_by_mutation(
    gene_symbol: str, raw_input: str, limit: int = 10
) -> List[VariantInputModel]:
    terms = _normalize_variant_input(raw_input)

    print("=" * 50)
    print(f"Gene: {gene_symbol}, Raw input: {raw_input}")
    print(f"Normalized terms: {[t.lower() for t in terms]}")

    r = httpx.get(f"{EUTILS_BASE}/esearch.fcgi", params={
        "db": "clinvar",
        "term": f"{gene_symbol}[gene]",
        "retmax": 50,
        "retmode": "json",
    })
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    print(f"IDs from gene search: {len(ids)}")

    if not ids:
        print("No variants found for this gene.")
        print("=" * 50)
        return []

    time.sleep(0.4)

    variants, _ = fetch_summaries(ids)
    matched = [v for v in variants if _title_matches(v.title, terms)]

    print(f"Total variants: {len(variants)}, matched '{raw_input}': {len(matched)}")
    for v in matched:
        print(f"  - {v.tag} | {v.title} | {v.clinical_significance}")
    print("=" * 50)

    return matched[:limit]


def search_diseases_clinvar(query: str, limit: int = 20) -> List[DiseaseInputModel]:
    r = httpx.get(f"{EUTILS_BASE}/esearch.fcgi", params={
        "db": "clinvar",
        "term": f"{query}[disease]",
        "retmax": limit * 3,
        "retmode": "json"
    })
    ids = r.json().get("esearchresult", {}).get("idlist", [])

    if not ids:
        return []

    time.sleep(0.4)
    _, diseases = fetch_summaries(ids)

    seen = set()
    unique = []
    for d in diseases:
        if d.tag not in seen:
            seen.add(d.tag)
            unique.append(d)

    return unique[:limit]


def clinvar_variant_to_genotype_components(
    variant: VariantInputModel,
    protein_tag: str,
    proteome_tag: str,
) -> list:
    """
    Convert a VariantInputModel into a list of AttributeTree-compatible dicts
    ready to be passed as `components` in InsertGeneticApplicationModel.
    """

    CONSEQUENCE_MAP = {
        "missense variant":        "att_protein_mutation:substitution",
        "nonsense":                "att_protein_untargeted_mutation:premstop",
        "frameshift variant":      "att_protein_untargeted_mutation:frameshift",
        "stop gained":             "att_protein_untargeted_mutation:premstop",
        "synonymous variant":      "att_protein_mutation:none",
        "splice acceptor variant": "att_protein_untargeted_mutation:frameshift",
        "splice donor variant":    "att_protein_untargeted_mutation:frameshift",
        "deletion":                "att_protein_mutation:deletion",
        "insertion":               "att_protein_mutation:insertion",
    }
    consequence_raw = (variant.consequence or "").lower().strip()
    mutation_trait_tag = CONSEQUENCE_MAP.get(consequence_raw, "att_protein_mutation:substitution")

    # extract aa position from title e.g. NM_003172.4(SURF1):c.770G>A (p.Gly257Glu)
    aa_position = None
    m = re.search(r'p\.[A-Z][a-z]{2}(\d+)[A-Z][a-z]{2,3}', variant.title)
    if m:
        aa_position = m.group(1)
    else:
        m2 = re.search(r'p\.[A-Z](\d+)[A-Z*]', variant.title)
        if m2:
            aa_position = m2.group(1)

    # att_protein node
    att_protein_trait = {
        "tag": proteome_tag,
        "type": "trait",
        "value": protein_tag,
        "children": [],
    }
    att_protein_node = {
        "tag": "att_protein",
        "type": "attribute",
        "value": None,
        "children": [att_protein_trait],
    }

    # att_protein_mutation node (with optional position)
    mutation_children = []
    if aa_position:
        aa_position_value_trait = {
            "tag": "att_aa_position:aa",
            "type": "trait",
            "value": aa_position,
            "children": [],
        }
        aa_position_node = {
            "tag": "att_aa_position",
            "type": "attribute",
            "value": None,
            "children": [aa_position_value_trait],
        }
        protein_position_trait = {
            "tag": "att_protein_position:aa",
            "type": "trait",
            "value": None,
            "children": [aa_position_node],
        }
        protein_position_node = {
            "tag": "att_protein_position",
            "type": "attribute",
            "value": None,
            "children": [protein_position_trait],
        }
        mutation_children = [protein_position_node]

    # determine attribute tag based on consequence
    is_untargeted = mutation_trait_tag.startswith("att_protein_untargeted_mutation")
    mutation_attribute_tag = "att_protein_untargeted_mutation" if is_untargeted else "att_protein_mutation"

    att_protein_mutation_node = {
        "tag": mutation_attribute_tag,
        "type": "attribute",
        "value": None,
        "children": [{
            "tag": mutation_trait_tag,
            "type": "trait",
            "value": None,
            "children": mutation_children,
        }],
    }

    # att_gene_zygosity node -> unknown for ClinVar variants
    zygosity_node = {
        "tag": "att_gene_zygosity",
        "type": "attribute",
        "value": None,
        "children": [{
            "tag": "att_gene_zygosity:unknown",
            "type": "trait",
            "value": None,
            "children": [],
        }],
    }

    # root: att_gene_engineering:natural_variant
    # no editing method -> naturally occurring variant, not lab-engineered
    root = {
        "tag": "att_gene_engineering",
        "type": "attribute",
        "value": None,
        "children": [{
            "tag": "att_gene_engineering:natural_variant",
            "type": "trait",
            "value": None,
            "children": [att_protein_node, zygosity_node, att_protein_mutation_node],
        }],
    }

    return [root]