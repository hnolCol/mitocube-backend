# SP3-Based Protein Digestion Protocol

## Summary

**Goal:** To reduce and alkylate proteins prior to enzymatic digestion, and to perform an SP3 bead-based sample cleanup and tryptic/Lys-C digestion of 25 µg protein starting material, yielding purified peptides suitable for LC-MS/MS analysis.

**Procedure overview:** Proteins were reduced (10 mM TCEP) and alkylated (20 mM CAA) in the dark for 45 min at 45 °C. 25 µg protein were subjected to an SP3-based digestion. Washed SP3 beads (a 1:1 mix of hydrophobic Sera-Mag™ Magnetic Carboxylate Modified Particles, GE44152105050250, and hydrophilic Sera-Mag™ Magnetic Carboxylate Modified Particles, GE24152105050250, from Sigma Aldrich) were combined, and 3 µL of bead slurry were added to each sample. Acetonitrile was added to a final concentration of 50%, and beads were washed twice with 70% ethanol (V = 200 µL) on an in-house manufactured magnet. After an additional acetonitrile wash (V = 200 µL), 5 µL of digestion solution (10 mM HEPES pH 8.5 containing 0.5 µg Trypsin (Sigma) and 0.5 µg LysC (Wako)) was added to each sample and incubated overnight at 37 °C. Peptides were desalted on a magnet using 2 × 200 µL acetonitrile, then eluted in 10 µL 5% DMSO in LC-MS water (Sigma Aldrich) via ultrasonic bath for 10 min. Formic acid and acetonitrile were added to final concentrations of 2.5% and 2%, respectively. Samples were stored at −20 °C prior to LC-MS/MS analysis.

**Result:** Reduced, alkylated, and enzymatically digested peptides—cleaned up and concentrated via SP3 bead binding/washing/elution—ready for downstream desalting (StageTip) and LC-MS/MS analysis.

---

## Step-by-Step Guide

### Equipment
- Magnetic stand for PCR tubes (self-made)
- PCR tubes with individually attached lids
- Ultrasonic Cleaner USC-THD/HF (VWR)
- Thermomixer C (Eppendorf, 96-well block)

### Materials/Solutions
- SP3 beads:
  - Sera-Mag™ Magnetic Carboxylate Modified Particles (Hydrophobic), GE44152105050250
  - Sera-Mag™ Magnetic Carboxylate Modified Particles (Hydrophilic), GE24152105050250
- 100% Acetonitrile (ACN) (VWR, 83642.290)
- 70% Ethanol absolute (EtOH) (VWR, 20821.321)
- 100% Dimethylsulfoxide (DMSO) (Roth, A994.2)
- 10 mM / 100 mM HEPES-KOH pH 8.5 (Hepes, Sigma, H4034-100g)
- Water, Optima LC/MS (Fisher Chemicals, W6-1)
- Lys C (1 µg/µL) (Fujifilm Wako Chemicals Europe, 129-02541; resuspended in LC/MS water)
- Trypsin (1 µg/µL) (Sigma, T6567-1mg; resuspended in 1 mM HCl)
- TCEP (0.5 M stock) — Tris(2-carboxyethyl)phosphine hydrochloride solution (Sigma, 646547-10x1mL)
- CAA (1 M stock) — 2-Chloroacetamide (Sigma, C0267-500g)

---

### 1. Preparing the Beads
1. Resuspend beads gently on a vortexer until completely resuspended.
2. Mix 160 µL LC/MS water with 20 µL hydrophilic beads and 20 µL hydrophobic beads.
3. Place on magnet for 3 min.
4. Remove liquid.
5. Wash 3 times with water on the magnet.
6. Remove liquid.
7. Resuspend in 100 µL water (beads are stable for 2–3 weeks).

### 2. Binding Protein to Beads
1. Add 3 µL beads into PCR tubes.
2. Add sample.
3. Add an equal volume of ACN (final 50%).
4. Incubate 8 min.
5. Place on magnet for 3 min.
6. Remove liquid.

### 3. Washing (always on magnet)
1. Add 180 µL 70% EtOH; remove liquid.
2. Add 180 µL 70% EtOH; remove liquid.
3. Add 180 µL 100% ACN; remove liquid.
4. Let beads dry (beads should appear light brown).

### 4. Reduction and Alkylation
*(Normally performed before digestion; only performed on-bead for IPs.)*
1. Resuspend sample in ~40 µL LC/MS water.
2. Add TCEP to a final concentration of 10 mM.
3. Incubate at 45 °C, 15 min, 550 rpm.
4. Add CAA to a final concentration of 20 mM.
   - **Note:** CAA is light-sensitive — protect from light.
5. Incubate at 45 °C, 30 min, 550 rpm, in the dark.

**4a. Binding Protein to Beads**
1. Add an equal volume of ACN (final 50%).
2. Incubate 8 min.
3. Place on magnet for 3 min.
4. Remove liquid.

**4b. Washing (always on magnet)**
1. Add 200 µL 70% EtOH; remove liquid.
2. Add 200 µL 70% EtOH; remove liquid.
3. Add 200 µL 100% ACN; remove liquid.
4. Let beads dry (beads should appear light brown).

### 5. Digest
1. Add 5 µL digest solution (small volume to achieve a high ACN concentration the next day):
   - Protein:enzyme ratio — 100:1
   - If protein concentration is unknown, use 0.1 µg Trypsin and 0.1 µg Lys C
   - Buffer: 100 mM HEPES pH 8.5
2. Incubate overnight at 37 °C, 550 rpm.

### 6. Binding Peptides to Beads
1. The next day, resuspend by vortexing.
2. Add 200 µL 100% ACN (>95% final concentration).
3. Incubate 8 min.
4. Place on magnet for 5 min.
5. Remove liquid (check that beads remain visible in the tips before discarding liquid).
6. Wash with 180 µL 100% ACN.
7. Remove liquid.
8. Let beads dry.

### 7. Elution of Peptides
1. Resuspend in 10 µL 5% DMSO (always prepare fresh).
2. Place in ultrasonic bath for 10 min.
3. Place on magnet for 3 min.
4. Transfer sample to a new tube.
5. Add 90 µL Buffer A.
6. Continue with the StageTip protocol.
