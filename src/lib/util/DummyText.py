import random
from typing import Tuple
class DummyText:
    _joke_lib: Tuple[str] = ("What do you call a sheep who can sing and dance? Lady Ba Ba.",
                             "Why can't dinosaurs clap their hands? Because they're extinct.",
                             "Dogs can't operate MRI machines. But catscan.",
                             "What do you call a dog who meditates? Aware wolf.",
                             "What has five toes and isn't your foot? My foot.",
                             "What do you call it when a cow grows facial hair? A moo-stache.",
                             "What did the beach say when the tide came in? Long time no sea.",
                             "What did the 0 say to the 8? Nice belt!",
                             "This is no time for jokes, guys. Let's B. cereus.",
                             "I've always wanted to publish a review on the role of Wnt antagonists in caudal outgrowth and specification in vertebrates. I'd title it 'Sonic Hedgehog and Tails'.",
                             "Why is 69 so scared of 70? Because once they fought and seven won.",
                             "Why was six afraid of seven? Because seven ate nine!",
                             "Two blood cells met and fell in love. Sadly, it was all in vein.",
                             "Why did the computer show up at work late? It had a hard drive.",
                             "Autocorrect can go straight to he’ll.",
                             "Biologists can also be great philosophers. They give fantastic life lessons.",
                             "Y’all want to hear a potassium joke? K.",
                             "Why do ants never get sick? Because they have little anty bodies.",
                             "No matter how popular they get, antibiotics will never be viral.",
                             "Which biochemicals wash up on beaches? Nucleotides.",
                             "What do you get when you cross a unit of data with a female pop singer?, A Gaga byte."
                             "My boss told me to have a good day, so I went home.",
                             "The rotation of earth really makes my day.")

    def __init__(self, dummy_text: Tuple[str]):
        self._dummy_text: Tuple[str] = dummy_text

    def get_full_text(self) -> str:
        return "\n".join(self._dummy_text)

    def get_text(self, n_characters: int, char_paragraph_separator = " ") -> str:
        it = 0
        dummy_text = self._dummy_text[0]

        while n_characters > len(dummy_text) & it < len(self._dummy_text) - 1:
            it += 1
            dummy_text = dummy_text + char_paragraph_separator + self._dummy_text[it]

        return dummy_text[0:n_characters]

    def get_paragraphs(self, n: int) -> str:
        if n < 1 or n > len(self._dummy_text):
            n = len(self._dummy_text)

        return "\n".join(self._dummy_text[0:n])

    @staticmethod
    def get_joke() -> str:
        return DummyText._joke_lib[random.randint(0, len(DummyText._joke_lib)-1)]
