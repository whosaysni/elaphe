# -*- coding: utf-8 -*-
# Copyright (c) 2010 Yasushi Masuda. All rights reserved.
"""
Symbology-specific message translations.

Tranlation object parforms conversion from message to sequence of
ordinals, to support alphabets/escape-sequences for individual
symbologies.

"""
import string

class TranslationError(ValueError):
    """
    Exception raised for errors during translation process.
    Kind of ValueError.

    >>> issubclass(TranslationError, ValueError)
    True
    """
    pass


class Translation(object):
    """
    Abstract base class for translations.

    Translation class has one public method, ``translate()``
    which converts message into sequence of ordinals.

    >>> t = Translation()
    >>> t # doctest: +ELLIPSIS
    <...Translation object at ...>

    ``translate()`` ordinally returns generator.
    >>> g = t.translate('spam eggs')
    >>> g # doctest: +ELLIPSIS
    <generator object translate at ...>

    ``Translation`` does not implement translate_chars to cause error.
    >>> list(g)
    Traceback (most recent call last):
    ...
    TypeError: This type has no valid translate_chars() implementation.
    
    """
    # singletons
    class RAISE_ON_ERROR(object): pass
    class IGNORE_ON_ERROR(object): pass

    def __init__(self, **kwargs):
        """Constructor.
        """

    def reset(self):
        """Resets internal status. Subclass may override.
        """

    def translate(self, message, on_error=None, **kwargs):
        """Converts sequence of ordinals to message string.
        """
        self.reset()
        queue = []
        for char in message:
            queue.append(char)
            ordinal = None
            try:
                ordinal = self.translate_chars(queue)
            except TranslationError, e:
                if on_error == self.RAISE_ON_ERROR:
                    raise e
                if on_error == self.IGNORE_ON_ERROR:
                    queue = []
                elif on_error is not None:
                    # clear queue, yield replacement and go on
                    queue = []
                    yield on_error
                else:
                    # defaults to ignore,
                    queue = []
            except:
                raise
            if ordinal is None:
                # wait for next char
                continue
            elif ordinal is NotImplemented:
                raise TypeError(u'This type has no valid '
                                'translate_chars() implementation.')
            else:
                # clear queue, yield something not None.
                queue = []
                yield ordinal
    
    def translate_chars(self, chars):
        return NotImplemented


class CharMapTranslation(Translation):
    """
    Translation using character map.

    >>> cmt = CharMapTranslation('+0123456789')
    >>> cmt # doctest: +ELLIPSIS
    <...CharMapTranslation object at ...>

    ``CharMapTranslation.map`` indicates internal translation map.
    >>> sorted(cmt.map.items()) # doctest: +ELLIPSIS
    [('+', 0), ('0', 1), ... ('8', 9), ('9', 10)]

    ``translate()`` yields sequence of ordinals.
    >>> list(cmt.translate('+++1357+++'))
    [0, 0, 0, 2, 4, 6, 8, 0, 0, 0]

    Invalid chars are ignored at default.
    >>> list(cmt.translate('1234xx'))
    [2, 3, 4, 5]

    Explicit RAISE_ON_ERROR will raise TranslatonError exception.
    >>> list(cmt.translate('1234xx', on_error=Translation.RAISE_ON_ERROR))
    Traceback (most recent call last):
    ...
    TranslationError: x not in allowed chars: +0123456789

    Explicit IGNORE_ON_ERROR behave same as default.
    >>> list(cmt.translate('1234xx', on_error=Translation.IGNORE_ON_ERROR))
    [2, 3, 4, 5]

    Replacement chars for ``on_error`` yields itself.
    >>> list(cmt.translate('1234xx', on_error='#'))
    [2, 3, 4, 5, '#', '#']

    ``offset`` and ``skip_char`` are for non-ordinal alphabets.
    >>> cmt = CharMapTranslation('0*1*2*3*4', offset=100, skip_char='*')
    >>> sorted(cmt.map.items()) # doctest: +ELLIPSIS
    [('0', 100), ('1', 102), ('2', 104), ('3', 106), ('4', 108)]
    >>> list(cmt.translate('2413'))
    [104, 108, 102, 106]

    """
    def __init__(self, chars, offset=0, skip_char=None, 
                 **kwargs):
        """
        Constructor.

        Accepts a positional argument ``char``, and two optional
        parameters: ``offset`` and ``skip_char``.
        """
        super(CharMapTranslation, self).__init__(**kwargs)
        self.allowed_chars = chars
        if skip_char:
            self.allowed_chars.replace(skip_char, '')
        self.map = dict(
            (char, idx+offset) 
            for idx, char in enumerate(chars) 
            if char!=skip_char)

    def translate_chars(self, chars):
        """
        Performs per-char translation.

        Multiple characters in chars are not allowed.
        """
        if len(chars)>1:
            raise TranslationError(u'Multiple characters not allowed.')
        # else
        char = chars[0]
        if char not in self.map:
            raise TranslationError(
                u'%(char)s not in allowed chars: %(allowed_chars)s' 
                %dict(char=char, allowed_chars=self.allowed_chars))
        # else
        return self.map.get(char)


class Code128Translation(Translation):
    """
    Converts message to code128 ordinals. Accepts cap('^')-escaped non-printables.

    >>> c128t = Code128Translation()
    >>> c128t # doctest: +ELLIPSIS
    <...Code128Translation object at ...>

    Escaped characters are processed successfully.
    >>> list(c128t.translate('^103AZ_^^_\\0\\1\\2', on_error=Translation.RAISE_ON_ERROR))
    [103, 33, 58, 63, 62, 63, 64, 65, 66]
    >>> list(c128t.translate('^104AZ_^^_\\x60ab', on_error=Translation.RAISE_ON_ERROR))
    [104, 33, 58, 63, 62, 63, 64, 65, 66]
    >>> list(c128t.translate('^105^102^', on_error=Translation.RAISE_ON_ERROR))
    [105, 102]
    >>> list(c128t.translate('^105^102123456^100A1', on_error=Translation.RAISE_ON_ERROR))
    [105, 102, 12, 34, 56, 100, 33, 17]
    >>> list(c128t.translate('^105^102123456^100A1', on_error=Translation.RAISE_ON_ERROR))
    [105, 102, 12, 34, 56, 100, 33, 17]

    Invalid character raises TranslationError (provided on_error is set).
    >>> list(c128t.translate('^105^X', on_error=Translation.RAISE_ON_ERROR))
    Traceback (most recent call last):
    ...
    TranslationError: ^X is not allowed for Code128 escape sequence.
    >>> list(c128t.translate('^105^X^102'))
    [105, 102]
    
    """
    ASCII_7BITS = ''.join(chr(i) for i in range(128))
    CODE_A_TABLE = ASCII_7BITS[32:96] + ASCII_7BITS[:32]
    CODE_B_TABLE = ASCII_7BITS[32:128]
    CODE_TABLES = dict(A=CODE_A_TABLE, B=CODE_B_TABLE)

    @staticmethod
    def cap_escape(s):
        """
        Converts string to cap-escaped printables.

        >>> cap_escape = Code128Translation.cap_escape
        >>> cap_escape('abcdef')
        'abcdef'
        >>> cap_escape('\\1\\2\\3\\10\\20\\30\\110\\120\\130\\200\\210\\220\\240')
        '^1^2^3^8^16^24HPX^128^136^144^160'
        """
        return ''.join(c if c in string.printable else '^'+str(ord(c))
                       for c in s)

    def __init__(self, **kwargs):
        super(Code128Translation, self).__init__(**kwargs)
        self.code = None

    def reset(self):
        """Resets internal code status.
        """
        self.code = None

    def translate_chars(self, chars):
        """
        Translates characters according to Code128 rules.

        The method employs internal mode stored in ``code`` instance attribute.
        
        >>> c128t = Code128Translation()
        >>> c128t.code # None
        >>> c128t.translate_chars(list('^')) # None
        >>> c128t.translate_chars(list('^^'))
        62

        # Shift code to A
        >>> c128t.translate_chars(list('^101'))
        101
        >>> c128t.code
        'A'
        >>> c128t.translate_chars(list('Z'))
        58

        # Shift code to B
        >>> c128t.translate_chars(list('^104'))
        104
        >>> c128t.code
        'B'

        # Shift code to C
        >>> c128t.translate_chars(list('^99'))
        99
        >>> c128t.code
        'C'
        """
        if chars[0] == '^':
            if len(chars)==1:
                # escape in
                return
            else:
                # escaped already
                if chars[1] == '^':
                    return 62
                else:
                    escaped = ''.join(chars[1:])
                    if escaped.isdigit():
                        ordinal = int(escaped, 10)
                        if ordinal<96:
                            return
                        elif ordinal in range(96, 108):
                            if ordinal in (99, 105):
                                self.code = 'C'
                            elif ordinal in (100, 104):
                                self.code = 'B'
                            elif ordinal in (101, 103):
                                self.code = 'A'
                            return ordinal
                        else: 
                            # ordinal larger than 108
                            pass
                    # ordinal larger than 108, or invalid escape sequence
                    raise TranslationError(
                        u'^%s is not allowed for Code128 escape sequence.' 
                        %(escaped))
        else:
            ordinal = None
            if self.code in ['A', 'B']:
                code_table = self.CODE_TABLES[self.code]
                try:
                    ordinal = code_table.index(chars[0])
                except IndexError:
                    raise TranslationError(
                        u'%(char)s is not in code table %(code)s'
                        %(dict(char=chars[0], code=self.code)))
            elif self.code == 'C':
                # requires two chars to continue
                if len(chars)==2:
                    ordinal = int(''.join(chars), 10)
                else:
                    return
            return ordinal


# translation shortcuts 
code39 = CharMapTranslation(
    '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%').translate
digits = CharMapTranslation('0123456789').translate
nw7 = CharMapTranslation('0123456789-$:/.+ABCD').translate
code128 = Code128Translation().translate


if __name__=="__main__":
    from doctest import testmod
    testmod()
