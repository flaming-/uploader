#!/usr/bin/env python3
"""
py3bencode - GPL Bencode module developed for Python 3.

= Motivation =
  There already have been some Bencode modules for Python, but I haven't
  found any reliable module which works with Python 3 as well.
  So I created this module from scratch.
= Credits =
  Robert Nitsch <r.s.nitsch+dev@gmail.com> - July 2010 (Version 1.0)
= License =
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.

= flaming changes =

  flaming edited Nov 2012 to change to Python 2.5
  which btw was a bitch.
  
"""

def _bytes(_str):
    """
    Convert ordinary Python string (utf-8) into byte array (should be considered
    as c-string).

    @rtype:   bytes

    flaming edit:
    python 2.5 doesn't have bytes() or even bytearray() so we just bootleg it
    with str(), heh.
    """
    return str(_str)

def _str(_bytes):
    """
    Attempt to decode byte array back to ordinary Python string (utf-8).

    Decoding cannot be guaranteed, so be careful.

    @rtype:   str, but will return the original data if it can't be interpreted
    as utf-8

    flaming edit:
    this function is useless
    """
    return _bytes

def bencode(thing):
    """
    bencodes the given object, returning a string
    containing the bencoded data.

    Allowed object types are:
    - list (list)
    - dictionary (dict)
    - integer (int)
    - string (str)

    @rtype:   str

    flaming edit:
    this function uses strings now... no functionality lost... I don't
    understand what the advantage of using bytes was in the first place.
    """
    if   isinstance(thing, int):
        return _bytes("i%se" % thing)

    elif isinstance(thing, str):
        return _bytes(str(len(_bytes(thing))) + ":" + thing)

    elif isinstance(thing, list):
        return 'l%se' % ''.join([bencode(i) for i in thing])
    
    elif isinstance(thing, dict):
        result = 'd'
        
        keys = list(thing.keys())
        keys.sort()
        for key in keys:
            result += bencode(key) + bencode(thing[key])

        return result + 'e'

    raise TypeError("bencoding objects of type %s not supported" % type(thing))

def bdecode(data, decode_strings=True, strict=False):
    """
    Restores/decodes bencoded data. The bencoded data must be given as byte array.

    Note that all bencode-strings are treated as byte arrays first. Unless
    decode_strings=False the bdecoder then tries to convert every byte array
    to an ordinary Python string, that means: it tries to interpret every
    byte string as utf-8 string.

    This behavior is meant to make this module more convenient.
    Though I strongly recommend to disable the automatic decoding attempts of
    strings. Your application should know which bencode-strings are meant to
    be utf-8 and which not.

    The strict parameter enforces additional bencode conventions, these are:
    - no negative zeroes are allowed for integers
    - no leading  zeroes are allowed for integers

    strict=False (default) means the decoder will just ignore glitches like that.
    Please note that a proper encoder will never produce errors like these at all.

    @rtype:   list, dict, int, str

    flaming edit:
    this is useless for my project's purposes but i guess i'll keep it for
    future-proofing...?    
    """
    if not isinstance(data, str):
        raise TypeError("bdecode expects string.")

    return BDecoder(data, decode_strings, strict).decode()

class DecodingException(Exception):
    """
    Raised by the decoder on error.
    """
    pass

class BDecoder(object):
    """
    The decoder itself.

    See bdecode() for how to use it. (Though I recommend not to do so.)
    """
    def __init__(self, data, decode_strings, strict):
        self.data   = data
        self.pos    = 0

        self.strict         = strict
        self.decode_strings = decode_strings

    def get_pos_char(self):
        """
        Get char (str) at current position.
        """
        _res = self.data[self.pos:self.pos+1]

        # why use slice syntax instead of ordinary random access?
        # because self.data[some_index] would return a byte,
        # that is a number between 0-255.
        #
        # slice syntax, however, returns e.g. b'A' (instead of 65).
        #
        # flaming edit: this is irrelevant when using str

        if len(_res) == 0:
            raise DecodingException(
                "Unexpected end of data. Unterminated list/dictionary?")
        return _res
    pos_char = property(get_pos_char)

    def decode(self):
        """Decode whatever we find at the current position."""
        _pos_char  =  self.pos_char

        if   _pos_char == 'i':
            self.pos  +=  1
            return self.decode_int()
        elif _pos_char == 'l':
            self.pos  +=  1
            return self.decode_list()
        elif _pos_char == 'd':
            self.pos  +=  1
            return self.decode_dict()
        elif _pos_char.isdigit():
            return self.decode_string()
        else:
            raise DecodingException

    def decode_int(self):
        _start = self.pos
        _end   = self.data.index('e', _start)

        if _start == _end:
            raise DecodingException("Empty integer.")

        self.pos = _end+1

        _int = int(self.data[_start:_end])

        # strict: forbid leading zeroes and negative zero
        if self.strict:
            if bytes(str(_int), "utf-8") != self.data[_start:_end]:
                raise DecodingException("Leading zeroes or negative zero detected.")

        return _int

    def decode_list(self):
        _list = []

        while True:
            if self.pos_char == 'e':
                self.pos += 1
                return _list

            _pos = self.pos

            try:
                _list.append(self.decode())
            except DecodingException:
                # did the exception happen because there is nothing to decode?
                if _pos == self.pos:
                    raise DecodingException("Unterminated list (or invalid list contents).")
                else:
                    raise

        assert False

    def decode_dict(self):
        _dict = {}

        while True:
            if self.pos_char == 'e':
                self.pos += 1
                return _dict

            if not self.pos_char.isdigit():
                raise DecodingException("Invalid dictionary key (must be string).")

            key        = self.decode_string()
            _dict[key] = self.decode()

        assert False

    def decode_string(self):
        _start = self.pos
        _colon = self.data.index(':', _start)
        _len   = int(self.data[_start:_colon])

        if _len < 0:
            raise DecodingException("String with length < 0 found.")

        self.pos = _colon+1+_len

        _res = self.data[_colon+1:_colon+1+_len]

        if self.decode_strings:
            return _str(_res)
        else:
            return _res
