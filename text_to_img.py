""" Text to image staff. """
from functools import cached_property
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

BACKGROUND_COLOR = (255, 255, 255)  # white color supported only
FONT_COLOR = (0, 0, 0)  # black color supported only

EMOJI_FONT_PATH = "AppleColorEmoji.ttf"  # https://github.com/samuelngs/apple-emoji-linux
TEXT_FONT_PATH = "Disket-Mono-Bold.ttf"  # https://pro-catalog.ru/font/font-disket-mono-cyrillic/


class Font:
    """ Font model"""
    FONT_SIZE = 136  # both fonts supported size (the bigger the better)

    def __init__(self, path: str, example: str, additional_space: int = 0):
        self.path = path
        self.fnt = TTFont(path)
        self.img = ImageFont.truetype(path, size=self.FONT_SIZE)
        self.example = example

    @cached_property
    def letter_width(self) -> float:
        return self.img.getsize(self.example)[0] / len(self.example)

    @cached_property
    def letter_height(self) -> float:
        return self.img.getsize(self.example)[1]

    def has_symbol(self, letter: str):
        return any(ord(letter) in table.cmap.keys() for table in self.fnt['cmap'].tables)


class TextProcessor:
    """ Text processor model"""
    PIXELS_PER_LINE = 20  # symbols per line
    # russian words are meadian=4, max=25 symbol length
    IMAGE_PIX_WIDTH = PIXELS_PER_LINE * Font.FONT_SIZE

    def __init__(self, fonts: List[Font]):
        """
        Args:
            fonts: fonts to use (first overloads latter)
        """
        self.fonts = fonts

    def letters(self, text: str) -> List[Tuple[str, Font]]:
        """
        Split text into letters.
        Args:
            text: text to split
        Returns:
            words:
                [("<letter>", <letter font>)]
        """
        letters = []
        for letter in text.strip(' \n'):
            for font in self.fonts:
                if font.has_symbol(letter):
                    letters.append((letter, font))
                    break
            else:
                if letter == '\n':
                    letters.append(('\n', self.fonts[0]))
                elif letter == b'\xef\xb8\x8f'.decode():  # end of tg msg?
                    pass
                else:
                    # raise RuntimeError(f"Unknown symbol '{letter}'")
                    pass
        return letters

    def words(self, letters: List[Tuple[str, Font]]) -> List[Tuple[str, Font]]:
        """
        Joined letters into words.
        Args:
            letters: letters to join
        Returns:
            words:
                [("<word>", <word font>)]
        """
        words = []
        current_font = letters[0][1]
        current_word = []

        def new_word(font_):
            """ Start new word """
            if current_word:
                words.append((''.join(current_word), font_))
                current_word.clear()

        for letter, font in letters:
            if letter in {'\n', ' '}:
                new_word(current_font)
                if letter == '\n':
                    current_word.append(letter)
                    new_word(font)
                    continue
            if current_font == font:
                current_word.append(letter)
            else:
                new_word(font)
                current_word.append(letter)
                current_font = font
        new_word(current_font)
        return words

    def word_table(self, text: str) -> List[List[Tuple[str, Font]]]:
        """
        Create word table from input text.
        Args:
            text: input text
        Returns:
            word table
        """
        table: List[List[Tuple[str, Font]]] = [[]]
        line_pix_len = self.IMAGE_PIX_WIDTH

        def newline():
            """ Start new line """
            if table[-1]:
                nonlocal line_pix_len
                table.append([])
                line_pix_len = self.IMAGE_PIX_WIDTH

        def add_word(word_, font_):
            """ Dump word """
            nonlocal line_pix_len
            line_pix_len -= word_pix_length
            table[-1].append((word_, font_))

        words = self.words(self.letters(text))
        for word, font in words:
            if word == '\n':
                newline()
                continue
            word_pix_length = int(len(word) * font.letter_width + 1)
            if word_pix_length <= line_pix_len:  # OK
                add_word(word, font)
            elif word_pix_length <= self.IMAGE_PIX_WIDTH:  # not ok, but less
                newline()
                add_word(word, font)
            else:  # too big word
                lines_count = (word_pix_length - 1) // self.IMAGE_PIX_WIDTH + 1  # 20->2, 19->2, 21->3
                word_part_len = int(self.IMAGE_PIX_WIDTH // font.letter_height)
                for idx in range(lines_count):
                    newline()
                    word_part = word[idx * word_part_len:(idx + 1) * word_part_len]
                    add_word(word_part, font)
        return table

    def compile_text(self, text: str) -> Image.Image:
        """
        Compile text into image.
        Args:
            text: text to compile
        Returns:
            image with text
        """
        table = self.word_table(text)
        line_heigth = max(font.letter_height for font in self.fonts)
        size = (self.PIXELS_PER_LINE * Font.FONT_SIZE, line_heigth * len(table))
        img = Image.new("RGB", size, 0xffffff)
        draw = ImageDraw.Draw(img)
        counter = [0, 0]
        for line in table:
            for word, font in line:
                draw.text(counter, word, font=font.img, fill=0x000000)
                counter[0] += len(word) * font.letter_width
            counter[0] = 0
            counter[1] += line_heigth
        return img


TEXT_PROCESSOR = TextProcessor([
    Font(TEXT_FONT_PATH, example="English Русский"),
    Font(EMOJI_FONT_PATH, example="💃🌌🤠🙃❤🥰😕😃😔🤑", additional_space=20)]
)

if __name__ == '__main__':
    TEXT_PROCESSOR.compile_text("💃🌌🤠🙃❤🥰😕😃😔🤑\nEnglish\nРусский").show()
