"""A utility module for handling Fasta sequences, entries and files.

Copyright (c) 2011 Joel Hedlund.

Contact: Joel Hedlund <yohell@ifm.liu.se>
"""

__version__ = "4.0.0"

__copyright__ = """\
Copyright (c) 2005-2007 Joel Hedlund.  All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

  * Neither the name of the author nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import re
from StringIO import StringIO

GAP_CHARACTERS = '-.'

class FastaError(Exception):
    """Base class for exceptions in the fasta module."""
    message = None
    def __init__(self, message=None, params=None):
        self.message = message
        self.params = params

    def __str__(self):
        return (self.message or self.__class__.message) % (self.params or {})

class FormatError(FastaError):
    message = "entry is not in fasta format"

class EmptyInput(FastaError):
    """Raised when input text is only whitespace."""
    message = "no fasta entry present in input"

class NonUniqueIDError(FastaError):
    message = "sequence id %(id)s is duplicated"

class FastaEntry(object):
    def __init__(self, id=None, description='', sequence='', line_length=60):
        """A fasta entry.

        IN:
        id = None: <str>
            The entry ID.
        description = '': <str>
            The description. '' means not present.
        sequence = None: <str>
            The residues in the sequence. No whitespace allowed.
        line_length = 60: <int>
            Number of sequence letters per line when producing plaintext.

        """
        self.id = id
        self.description = description
        self.sequence = sequence
        self.line_length = line_length

    def __len__(self):
        if self.sequence:
            return len(self.sequence)
        return 0

    def __iter__(self):
        return iter(self.sequence)

    def __getitem__(self, index):
        return self.sequence[index]

    def __str__(self):
        lsEntry = [self.header]
        for i in range(0, len(self.sequence), self.line_length):
            lsEntry.append(self.sequence[i:i + self.line_length])
        return '\n'.join(lsEntry)

    @property
    def header(self):
        base = '>' + self.id
        if self.description:
            return base + ' ' + self.description
        return base

    @classmethod
    def from_text(cls, fasta_sequence):
        """Create a new FastaEntry object from parsing a plaintext sequence.

        The length of the whitespace between the ID and description (if
        present) carries no information and will therefore be ignored.
        """
        if isinstance(fasta_sequence, basestring):
            fasta_sequence = StringIO(fasta_sequence)
        fasta_sequence = iter(fasta_sequence)
        self = cls()
        for line in fasta_sequence:
            header = line.strip()
            if header.startswith(';'):
                continue
            if header:
                break
        else:
            raise EmptyInput
        if header[0] != '>':
            raise FormatError('illegal characters before header')
        parts = header.split(None, 1)
        if len(parts) == 0:
            raise FormatError('no sequence id')
        self.id = parts[0][1:]
        if len(parts) > 1:
            self.description = parts[1].strip()
        sequence = []
        for line in fasta_sequence:
            if line.strip().startswith(';'):
                continue
            sequence.extend(line.split())
        self.sequence = ''.join(sequence)
        return self

    def search(self, regex):
        """Search the sequence for the given regex.

        ValueError will be raised if no sequences match the regex.

        IN:
        regex: <str> or <regex>
            Will be used to .search() the sequence. Strings will be
            compiled into case insensitive regexes.

        OUT:
        A re.match object or None.

        """
        if isinstance(regex, str):
            regex = re.compile(regex, re.IGNORECASE)
        return regex.search(self.sequence)

    def search_aligned(self, motif):
        """Search for motifs that may have been gapped by an aligner.

        IN:
        motif: <str>
            The (ungapped) sequence motif to search for. This method will
            insert "[GAP_CHARS]*" between all characters in this str and
            compile a case insensitive regex wich will then be used to
            .search() the sequence.

        OUT:
        A re.match object or None.

        """
        sGaps = "[%s]*" % GAP_CHARACTERS
        r = re.compile(sGaps.join(motif), re.IGNORECASE)
        return r.search(self.sequence)

    def ungapped(self):
        """Return the sequence with all gap characters removed."""
        s = self.sequence
        for sGapChar in GAP_CHARACTERS:
            s = s.replace(sGapChar, '')
        return s

    def alignment_index(self, sequence_index):
        """Where can the given sequence index be found in the alignment?

        This will always return sequence_index for unaligned (non-gapped)
        sequences.

        IN:
        sequence_index: <int>
            A sequence residue index using python notation.

        OUT:
        An alignment index as an <int>. Example: .alignment_index(0)
        returns the index for the position where the first residue of the
        sequence is aligned.

        """
        if sequence_index >= len(self.ungapped()):
            raise IndexError("sequence index out of range")
        sequence_index %= len(self.ungapped())
        iCurrent = -1
        for i, sResidue in enumerate(self.sequence):
            if sResidue not in GAP_CHARACTERS:
                iCurrent += 1
            if iCurrent == sequence_index:
                return i

    def sequence_index(self, alignment_index):
        """Where can a given alignment index be found in the sequence?

        Will always return float(alignment_index) for unaligned
        (non-gapped) sequences.

        IN:
        alignment_index: <int>
            An alignment index using python notation.

        OUT:
        A sequence index as a <float>. If the given position is in the gap
        following sequence position X, then X + 0.5 will be returned. If
        the given sequence index is before the first aligned residue of the
        sequence then -0.5 will be returned, and if it is past the end of
        the sequence then len(self.ungapped()) - 0.5 will be returned.

        """
        if alignment_index > self.length():
            raise IndexError("alignment index out of range")
        s = self.sequence[:alignment_index]
        nSequenceIndex = float(alignment_index)
        for sGap in GAP_CHARACTERS:
            nSequenceIndex -= s.count(sGap)
        if self.sequence[alignment_index] in GAP_CHARACTERS:
            nSequenceIndex -= 0.5
        return nSequenceIndex

    def starts_before(self, alignment_index):
        """Is the first non-gap char located before (or at) this index?"""
        if alignment_index > self.length():
            raise IndexError("alignment index out of range")
        alignment_index %= self.length()
        for s in self.sequence[:alignment_index + 1]:
            if s not in GAP_CHARACTERS:
                return True
        return False

    def ends_after(self, alignment_index):
        """Is the last non-gap char located after (or at) this index?"""
        if alignment_index > self.length():
            raise IndexError("alignment index out of range")
        alignment_index %= self.length()
        for s in self.sequence[alignment_index:]:
            if s not in GAP_CHARACTERS:
                return True
        return False

    def in_sequence(self, alignment_index):
        """Does the sequence start before and end after this index?"""
        return self.starts_before(alignment_index) and self.ends_after(alignment_index)

    def present_in_slice(self, start, stop):
        """Is the sequence present in the slice defined by start and stop?"""
        return self.starts_before(start) and self.ends_after(stop - 1)

def parse_sequence(sequence):
    """Parse a string or file and return a FastaEntry. Convenience for FastaEntry.from_text()."""
    return FastaEntry.from_text(sequence)

def iter_entries(fasta, plaintext=False):
    """An iterator for FastaEntry objects.

    The fasta can be given either as a str or as a file. Set plaintext=True
    to return plaintext entries rather than parsed ones.

    """
    if isinstance(fasta, basestring):
        fasta = StringIO(fasta)
    lines = []
    build_entry = lambda lines: ''.join(lines) if plaintext else parse_sequence(lines)
    entries = 0
    for sLine in fasta:
        if sLine.startswith('>'):
            entries += 1
            if lines:
                yield build_entry(lines)
                lines = []
        elif not lines:
            if not entries:
                raise FormatError('junk data before first sequence header')
            raise FormatError
        lines.append(sLine)
    yield build_entry(lines)

class FastaList(list):
    """A standard list, but with .from_text() and .to_str() methods."""
    @classmethod
    def from_text(cls, fasta, plaintext=False):
        """Parse a fasta format string or file.

        Set plaintext=True to store plaintext entries rather than FastaEntry objects.

        Note that this method does not require all sequence IDs to be unique.
        """
        try:
            return cls(iter_entries(fasta, plaintext))
        except EmptyInput:
            return cls()

    def to_str(self):
        """Return all entries in plaintext as a single str."""
        return '\n'.join(str(entry) for entry in self)

class FastaDict(dict):
    """A standard dict, but with .from_text() and .to_str() methods."""
    @classmethod
    def from_text(cls, fasta, plaintext=False):
        """Parse a fasta format string or file.

        Requires all sequence ids to be unique, or will raise NonUniqueIDError.

        Set plaintext=True to store plaintext entries rather than FastaEntry objects.
        Note that this will parse all entries anyway, in order to get the ids properly.

        """
        ids = set([])
        def get_id(entry):
            if entry.id in ids:
                raise NonUniqueIDError(params=dict(id=id))
            ids.add(entry.id)
            return entry.id
        try:
            return cls((get_id(e), str(e) if plaintext else e) for e in iter_entries(fasta, plaintext))
        except EmptyInput:
            return cls()

    def to_str(self):
        """Return all entries in plaintext as a single str."""
        return '\n'.join(str(entry) for entry in self.values())

def entries(fasta, plaintext=False):
    """Parse a fasta string or file and return a FastaList of FastaEntry objects.

    Set plaintext=True to return plaintext entries rather than parsed ones.

    """
    return FastaList.from_text(fasta, plaintext)

def fastadict(fasta, plaintext=False):
    """Parse a fasta string or file and return a FastaDict of FastaEntry objects.

    Set plaintext=True to return plaintext entries rather than parsed ones.

    Requires all sequence ids to be unique, or will raise NonUniqueIDError.
    """
    d = FastaDict.from_text(fasta, plaintext)
