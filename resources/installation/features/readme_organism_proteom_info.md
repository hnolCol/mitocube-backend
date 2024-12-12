# To prepare features ...

... download e.g. proteins from UNIPROT as TSV file. The following columns are critical and should be selected, column names may vary:

- "Entry Name" (in postgre DB, label)
- "Gene Names" (in postgre DB, gene_name)
- "Organism" or "Organism (ID)" (in postgre DB, organism_id)
- "Protein names" (in postgre DB, protein_name)
- "Proteomes" (in postgre DB, proteome_id)
- "Length" (in postgre DB, length_aa)
- "Mass" (in postgre DB, mass)
- "Sequence" (in postgre DB, sequence)
- "Reviewed" (in postgre DB, is_reviewed)


# Example Files and associated information:

Thought as help for what is required to fill the database tables plus to copy&paste commands / information together in the isntall script.

## Human
From Uniprot: `uniprotkb_AND_model_organism_9606_2024_12_11.tsv`

### Organism
- *taxon_id*: 9606
- *label*: "human"
- *mnemonic_name*: "HUMAN"
- *scientific_name*: "Homo sapiens"
- *common_name*: "Human"
- *phylum*: "Chordata"
- *description*: "Humans (Homo sapiens, meaning 'thinking man' or 'wise man') are the universe’s premier experts at simultaneously achieving the extraordinary and the utterly mundane. They’ve mastered everything from splitting atoms to misplacing sunglasses that were on their heads all along. Known for their curious minds, baffling bureaucracy, and love of tea, humans have built vast civilizations driven by their ingenuity, stubbornness, and an inexplicable fondness for shiny objects. While they’re often convinced of their own importance, the rest of the galaxy tends to view them as well-meaning but occasionally baffling creatures with a knack for getting into trouble—and somehow surviving it. Approach with caution, curiosity, and perhaps a towel."

### Proteom
- *proteome_id*: "UP000005640"
- *status*: "Reference proteome"
- *organism_id* / *organism_label*: "human"

## Mouse
From Uniprot: `uniprotkb_AND_model_organism_10090_2024_12_11.tsv`

### Organism
- *taxon_id*: 10090
- *label*: "mouse"
- *mnemonic_name*: "MOUSE"
- *scientific_name*: "Mus musculus"
- *common_name*: "Mouse"
- *phylum*: "Chordata"
- *description*: "Mice (Mus musculus, meaning 'tiny squeaky mastermind') are small, unassuming rodents who have quietly perfected the art of surviving anywhere and everywhere. To humans, they are humble creatures with twitchy noses and a fondness for cheese (a misconception, but they won’t correct it). To the rest of the galaxy, however, mice are known as highly intelligent beings running complex experiments on humanity under the guise of being 'adorable pests.' With their unparalleled adaptability and clandestine scheming, mice have managed to influence the course of history while nibbling on crumbs. Never underestimate a mouse—they’re likely smarter than you, and they know it."

### Proteom
- *proteome_id*: "UP000000589"
- *status*: "Reference proteome"
- *organism_id* / *organism_label*: "mouse"

## Rat
From Uniprot: `uniprotkb_AND_model_organism_10116_2024_12_11.tsv`

### Organism
- *taxon_id*: 10116
- *label*: rat
- *mnemonic_name*: "RAT"
- *scientific_name*: "Rattus norvegicus"
- *common_name*: "Rat"
- *phylum*: "Chordata"
- *description*: "Rats (Rattus spp., meaning 'long-tailed survivors') are the galaxy’s tireless overachievers, thriving in environments where most species would politely decline to exist. To humans, they’re plucky scavengers with a PR problem; to the universe at large, they’re resourceful strategists with no time for nonsense. Masters of adaptability, rats can outwit traps, navigate sewers like seasoned explorers, and turn a forgotten slice of pizza into a five-star feast. They’re not just survivors—they’re opportunists with flair. Approach a rat with respect and a bit of caution; it’s likely sizing you up as either a friend or an untapped resource."

### Proteom
- *proteome_id*: "UP000002494"
- *status*: "Reference proteome"
- *organism_id* / *organism_label*: "rat"

## Dogs
From Uniprot: ...

### Organism
- *taxon_id*: 9615
- *label*: "dog"
- *mnemonic_name*: "CANLF"
- *scientific_name*: "Canis lupus familiaris"
- *common_name*: "Dog"
- *phylum*: "Chordata"
- *description*: "Dogs (Canis lupus familiaris, meaning 'tail-wagging optimist') are widely regarded as the universe’s most enthusiastic carbon-based life forms. Known for their ability to form deep bonds with humans and their utter inability to understand the concept of personal space, dogs have earned their place as humanity’s most loyal companions and self-proclaimed cheerleaders. While often mistaken for simple creatures, dogs are, in fact, complex beings driven by a singular mission: to ensure every stick is chased, every snack is shared, and every human feels unconditionally loved—even when covered in drool. Approach a dog with kindness and maybe a treat; you’ll have a friend for life (or until you run out of snacks)."

### Proteom
- *proteome_id*: "UP000805418"
- *status*: "Reference proteome"
- *organism_id* / *organism_label*: "dog"

## Cats
From Uniprot: ...

### Organism
- *taxon_id*: 9685
- *label*: cat
- *mnemonic_name*: "FELCA"
- *scientific_name*: "Felis catus"
- *common_name*: "Cat"
- *phylum*: "Chordata"
- *description*: "Cats (Felis catus, meaning 'small, fuzzy overlord') are the galaxy’s most effective conquerors of hearts, homes, and furniture. Officially domesticated (though they would disagree), cats have mastered the art of convincing humans to serve their every whim while pretending to offer affection in return—when it suits them. Known for their agility, aloofness, and penchant for knocking things off tables, cats exude an aura of mystery and entitlement. Whether they're chasing lasers, napping in sunbeams, or judging you from a distance, cats are experts at maintaining their status as the universe’s most beloved freeloaders. Bow accordingly."

### Proteom
- *proteome_id* "UP000011712"
- *status*: "Reference proteome"
- *organism_id* / *organism_label*: "cat"

## C.elegans / cenorhabditis elegans
From Uniprot: ...

### Organism
- *taxon_id*: 6239
- *label*: celegans
- *mnemonic_name*: "CAEEL"
- *scientific_name*: "Caenorhabditis elegans"
- *common_name*: "Roundworm"
- *phylum*: "Nematoda"
- *description*: "Caenorhabditis elegans (C. elegans, meaning 'tiny wiggly overachiever') are microscopic nematodes best known for their uncanny ability to make humans feel intellectually inadequate despite having only 302 neurons. Widely studied by Earth’s scientists, these transparent, soil-dwelling worms have unlocked secrets of genetics, neuroscience, and aging—all while living their best wormy lives. To the rest of the galaxy, C. elegans are celebrated as minimalist geniuses: no frills, no drama, just efficient wriggling and groundbreaking science. Don’t let their size fool you; these worms are proof that sometimes, less really is more—especially if you’re trying to outsmart a lab full of humans."

### Proteom
- *proteome_id* "UP000001940"
- *status*: "Reference proteome"
- *organism_id* / *organism_label*: "celegans"

## Drosophila melanogaster
From Uniprot: ...

### Organism
- *taxon_id*: 7227
- *label*: "drosophila"
- *mnemonic_name*: "DROME"
- *scientific_name*: "Drosophila melanogaster"
- *common_name*: "Fruit fly"
- *phylum*: "Arthropoda"
- *description*: "Drosophila melanogaster (meaning 'fruit fly of the galaxy') are the universe's unsung heroes of genetics, known for their ability to change the course of scientific history while keeping their wings remarkably unruffled. Despite being small enough to be mistaken for a passing speck of dust, these tiny insects have played a starring role in over a century of genetic research, proving that size doesn’t matter when it comes to revolutionizing biology.  To the casual observer, they are merely pests in the fruit bowl; to researchers, they are indispensable tools, capable of solving mysteries like inheritance patterns and the effects of radiation—all while completing their life cycle in a mere 10 days. Approach with caution: one wrong move and they’ll have already finished their experiment."

### Proteom
- *proteome_id*: "UP000000803"
- *status*: "Reference proteome",
- *organism_id* / *organism_label*: "drosophila"


## Tomato 
From Uniprot: ...

### Organism
- *taxon_id*: 4081
- *label*: "tomato"
- *mnemonic_name*: "SOLLC"
- *scientific_name*: "Solanum lycopersicum"
- *common_name*: "Tomato"
- *phylum*: "Spermatophyta"
- *description*: "Solanum lycopersicum (meaning 'the plant that conquered pizza') is widely regarded as the fruit that doesn’t know it's a fruit and insists on being called a vegetable. Known by its more common name, the tomato, this unassuming plant has not only infiltrated nearly every cuisine on Earth, but it has also played a key role in global diplomacy (mostly through pizza, ketchup, and pasta sauces). Though often dismissed as a humble garden dweller, the tomato has quietly become a staple in the human diet, single-handedly transforming everything from salads to fast food menus. With its bright red, slightly squishy exterior, Solanum lycopersicum might look simple, but beneath the surface, it’s a fruit that knows its worth and will not be underestimated."

### Proteom
- *proteome_id* "UP000004994"
- *status*: "Reference proteome"
- *organism_id* / *organism_label*: "tomato"
