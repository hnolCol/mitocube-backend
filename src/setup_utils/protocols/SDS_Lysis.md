# SDS Lysis

## Summary
This protocol describes lysis of samples using SDS buffer combined with heat and ultrasonication, followed by reduction and alkylation of proteins. It also includes a colorimetric assay (Pierce 660 nm) to determine protein concentration in SDS-containing lysates, which is required before proceeding to downstream sample preparation steps (e.g., SP3, in-gel/in-solution digestion, phosphopeptide enrichment).

## Purpose
Used to efficiently lyse cells/tissue and solubilize proteins with SDS, and to reduce and alkylate cysteines in preparation for downstream proteomic sample processing.

---

## Part 1: SDS Lysis

### Equipment
- Thermomixer C (Eppendorf)
- Centrifuge 5430 R (Eppendorf)
- Sonopuls GM mini20 (Bandelin), sonotrode microtips MS 1.5 and MS 2.5
- 1.5 mL tubes with safe lock
- LoProtein binding tubes

### Materials, Solutions
- 4% SDS in HEPES-KOH buffer (10 mM, pH 8.5)
- HEPES-KOH (Sigma, H4034-100g)
- SDS pellets (Roth, CN30.1)
- TCEP, 0.5 M stock — Tris-(2-carboxyethyl)-phosphine hydrochloride solution (Sigma, 646547-10x1mL)
- CAA, 1 M stock — 2-Chloroacetamide (Sigma, C0267-500g)
- Water, Optima LC/MS (Fisher Chemical, W6-1)

### Procedure
1. Use tubes with safe lock (otherwise, do not heat samples above 70 °C)
2. Set Thermomixer C to 70 °C
3. Add 40 µL of 4% SDS buffer (pre-heated to 70 °C) to samples
4. Shake at 70 °C for 20–30 min
5. Lyse sample via ultrasonication
   - Check sonotrode type (1.5 mm or 2.5 mm)
   - Settings: amplitude 55–70%, time 30 sec, pulse 1 sec

### Reduction and Alkylation
1. Add TCEP to 10 mM final concentration
2. Incubate 15 min at 45 °C, 550 rpm
3. Add CAA to 20 mM final concentration
   - Note: CAA is light-sensitive! Keep CAA and CAA-treated samples in the dark
4. Incubate 30 min at 45 °C, 550 rpm
5. Centrifuge samples (18,213 × g, 10 min, RT)
6. Transfer samples to a new tube

---

## Part 2: Determination of Protein Concentration

### Equipment
- 96-well microplates, non-treated, clear, BRANDplates (BRAND)
- Microplate reader Epoch (BioTek)
- Centrifuge 5430 R (Eppendorf)

### Chemicals, Solutions
- Pre-diluted protein assay standards: Bovine Serum Albumin (BSA) set (125, 250, 500, 750, 1000, 1500, 2000 µg; Thermo Scientific, 23208)
- Pierce 660 nm Protein Assay Reagent (Thermo Scientific, 22660)
- Ionic Detergent Compatibility Reagent (IDCR) for Pierce 660 nm Protein Assay Reagent (Thermo Scientific, 22663)
- 4% SDS, 10 mM TCEP, 20 mM CAA in HEPES buffer (10 mM, pH 8.5)
- HEPES (Sigma, H4034-100g)
- SDS pellets (Roth, CN30.1)
- TCEP, 0.5 M stock — Tris-(2-carboxyethyl)-phosphine hydrochloride solution (Sigma, 646547-10x1mL)
- CAA, 1 M stock — 2-Chloroacetamide (Sigma, C0267-500g)

### Procedure
1. Pipet standards (10 µL) from lowest to highest concentration into a 96-well microplate
   - Prepare duplicates
2. Pipet blank into the microwell plate (9 µL water, 1 µL sample buffer)
3. Pipet sample into the microwell plate (9 µL water, µL sample)
4. Add 150 µL Pierce Protein Assay Reagent
   - When using SDS-containing solution, use Ionic Detergent Compatibility Reagent (IDCR) to inactivate SDS interference
   - **IDCR preparation:** 25 mL Pierce 660 nm Protein Assay Reagent + 1 g IDCR powder
     - Can be frozen at –20 °C
5. Mix with a multichannel pipette (if precipitate is visible)
6. Measure absorbance at 660 nm (reaction stable for up to 1 h)

---

## Next Steps
Continue with further sample preparation protocols as needed: SP3, NeoN, Phosphopeptide Enrichment, etc.
