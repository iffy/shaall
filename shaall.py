#!/usr/bin/env
"""
This program will compute the SHA of any file, including portions of a disk.

To run the tests do:

     python -m doctest -v shaall.py 
"""

from __future__ import print_function
from hashlib import sha256
import subprocess
import os
import math

MAX_BLOCK_SIZE = int(os.getenv('MAX_BLOCK_SIZE', 2 ** 20))

def isPowerOf2(x):
    """
    >>> isPowerOf2(2)
    True
    >>> isPowerOf2(1024)
    True
    >>> isPowerOf2(1025)
    False
    """
    log = int(math.log(x, 2))
    return 2**log == x

def listBounds(filesize, max_blocksize):
    """
    Return the chunks into which a file should be chunked so that the whole
    file can be read by dd

    >>> listBounds(9, 1024)
    [{'count': 1, 'skip': 0, 'bs': 9}]

    >>> listBounds(1025, 1024)
    [{'count': 1, 'skip': 0, 'bs': 1024}, {'count': 1, 'skip': 1024, 'bs': 1}]

    >>> listBounds(1026, 1024)
    [{'count': 1, 'skip': 0, 'bs': 1024}, {'count': 1, 'skip': 512, 'bs': 2}]

    >>> listBounds(2138934, 1024)
    [{'count': 2088, 'skip': 0, 'bs': 1024}, {'count': 1, 'skip': 4176, 'bs': 512}, {'count': 1, 'skip': 8354, 'bs': 256}, {'count': 1, 'skip': 66840, 'bs': 32}, {'count': 1, 'skip': 133682, 'bs': 16}, {'count': 1, 'skip': 534732, 'bs': 4}, {'count': 1, 'skip': 1069466, 'bs': 2}]
    
    """
    if not isPowerOf2(max_blocksize):
        raise Exception('Block size must be a power of 2')
    
    # small files
    if filesize < max_blocksize:
        return [{
            "skip": 0,
            "count": 1,
            "bs": filesize,
        }]
    
    # large files
    ret = []
    bytes_left = filesize
    blocksize = max_blocksize
    while bytes_left:
        blocks = bytes_left//blocksize
        if blocks:
            offset = filesize - bytes_left
            ret.append({
                "skip": offset//blocksize,
                "count": blocks,
                "bs": blocksize,
            })
        bytes_left -= blocks * blocksize
        blocksize /= 2

    return ret  

def shaPath(path, filesize, max_blocksize):
    """
    SHA a path using dd
    """
    bounds = listBounds(filesize, max_blocksize)
    s = sha256()
    for bound in bounds:
        sys.stderr.write('Reading chunk {0}\n'.format(bound))
        p_dd = subprocess.Popen([
            'dd',
            'bs={0}'.format(bound['bs']),
            'count={0}'.format(bound['count']),
            'skip={0}'.format(bound['skip']),
            'if={0}'.format(path),
        ], stdout=subprocess.PIPE)
        while True:
            data = p_dd.stdout.read(bound['bs'])
            if not data:
                break
            s.update(data)
    return s.hexdigest()

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if not args:
        print('''usage:
    {prog} size FILENAME
    {prog} hash FILENAME [SIZE]

more information:

    size FILENAME
    
        This command will print the size of FILENAME in bytes.

    hash FILENAME [SIZE]

        This command will compute the SHA256 of FILENAME.

        If FILENAME is an actual file, SIZE will default to the size
        of the file.  The following two commands are equivalent:

            {prog} hash FILENAME
            cat FILENAME | sha256sum

        If FILENAME is a disk (e.g. /dev/sda) then SIZE is
        required and determines how much of the disk to read to compute
        the hash.

        By default, a max block size of {max_block_size} B is used.  You
        may override this by setting the MAX_BLOCK_SIZE environment variable.
        MAX_BLOCK_SIZE must be a power of 2.

'''.format(
    prog=sys.argv[0],
    max_block_size=MAX_BLOCK_SIZE))
    else:
        subcommand = args[0]

        if subcommand == 'size':
            print(os.path.getsize(args[1]))
        elif subcommand == 'hash':
            filename = args[1]
            filesize = 0
            if len(args) == 3:
                filesize = int(args[2])
            else:
                filesize = os.path.getsize(filename)
            print(shaPath(filename, filesize, MAX_BLOCK_SIZE))
    