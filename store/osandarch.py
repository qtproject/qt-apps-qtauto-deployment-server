#############################################################################
##
## Copyright (C) 2018 Pelagicore AG
## Contact: https://www.qt.io/licensing/
##
## This file is part of the Neptune Deployment Server
##
## $QT_BEGIN_LICENSE:GPL-QTAS$
## Commercial License Usage
## Licensees holding valid commercial Qt Automotive Suite licenses may use
## this file in accordance with the commercial license agreement provided
## with the Software or, alternatively, in accordance with the terms
## contained in a written agreement between you and The Qt Company.  For
## licensing terms and conditions see https://www.qt.io/terms-conditions.
## For further information use the contact form at https://www.qt.io/contact-us.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3 or (at your option) any later version
## approved by the KDE Free Qt Foundation. The licenses are as published by
## the Free Software Foundation and appearing in the file LICENSE.GPL3
## included in the packaging of this file. Please review the following
## information to ensure the GNU General Public License requirements will
## be met: https://www.gnu.org/licenses/gpl-3.0.html.
##
## $QT_END_LICENSE$
##
## SPDX-License-Identifier: GPL-3.0
##
#############################################################################

# check for file type here.
# those are expected types
# ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 2.6.18, not stripped
# ELF 64-bit LSB shared object, x86-64, version 1 (GNU/Linux), dynamically linked, not stripped
# ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, not stripped
# Mach-O 64-bit x86_64 dynamically linked shared library
# Mach-O 64-bit x86_64 executable
# Mach-O universal binary with 2 architectures: [x86_64: Mach-O 64-bit x86_64 bundle] [i386: Mach-O i386 bundle] []
# PE32+ executable (console) x86-64, for MS Windows
# PE32+ executable (DLL) (console) x86-64, for MS Windows
# PE32+ executable (DLL) (GUI) x86-64, for MS Windows
# PE32+ executable (GUI) x86-64, for MS Windows

import re

def parseMachO(str):  # os, arch, bits, endianness
    if " universal " in str:
        # Universal binary - not supported
        raise Exception("Universal binaries are not supported in packages")
    os = "macOS"
    arch = str.split(' ')
    arch = arch[2]
    bits = str.split(' ')[1].replace('-bit', '')
    endianness = "little_endian"
    return [os, arch, bits, endianness]


def parsePE32(str):
    os = "Windows"
    arch = str.split(',')
    arch = arch[0]  # Take first part
    arch = arch.split(' ')
    arch = arch[-1]  # Take last element
    bits = '32'
    if arch == 'x86-64':
        bits = '64'
    if arch == '80386':
        arch = 'i386'
    endianness = "little_endian"
    return [os, arch, bits, endianness]


def parseElfArch(str, architecture, bits):
    architecture = architecture.strip()
    if architecture.startswith("ARM"):
        if 'aarch64' in architecture:
            return 'arm64'
        if 'armhf' in str:  # this does not work for some reason - from_file() returns longer data than from_buffer() - needs fix
            return 'arm'    # because qt does not report it directly
    elif architecture.startswith("Intel"):
        if '80386' in architecture:
            return 'i386'
    elif architecture.startswith("IBM S/390"):
        return 's/390'
    elif "PowerPC" in architecture:
        if bits == "64":
            return "power64"
        else:
            return 'power'
    # sparc architecture is currently ignored (should be handled similar to power?)
    return architecture.lower()


def parseElf(str):
    os = "Linux"
    arch = str.split(',')
    arch = arch[1]
    bits = str.split(' ')[1].replace('-bit', '')
    arch = parseElfArch(str, arch, bits)
    endian = str.split(' ')[2].lower()
    if endian == "msb":
        endianness = "big_endian"
    elif endian == "lsb":
        endianness = "little_endian"
    else:
        raise Exception("Unrecognised endianness")
    return [os, arch, bits, endianness]


def getOsArch(str):
    os = None
    arch = None
    bits = None
    endianness = None
    fmt = None
    if str.startswith("ELF "):
        fmt = "elf"
        os, arch, bits, endianness = parseElf(str)
    elif str.startswith("Mach-O "):
        fmt = "mach_o"
        os, arch, bits, endianness = parseMachO(str)
    elif str.startswith("PE32+ ") or str.startswith("PE32 "):
        fmt = "pe32"
        os, arch, bits, endianness = parsePE32(str)
    if arch:
        arch = arch.replace('-', '_')
    result = [os, arch, endianness, bits, fmt]
    if os:
        return result
    return None

def normalizeArch(inputArch):
    """
        This function brings requested architecture to common form (currently just parses the bits part and turns it into 32/64)
        Input string format is: arch-endianness-word_size-kernelType

    """
    parts = inputArch.split('-')
    #Drop anything non-numeric from word_size field
    parts[2]=re.sub(r"\D", "", parts[2])
    #Transform kernelType into binary format
    temp = parts[3]
    if "win" in temp:
        parts[3]="pe32"
    elif "linux" in  temp:
        parts[3]="elf"
    elif "freebsd" in temp: #How do we treat QNX?
        parts[3]="elf"
    elif "darwin" in temp:
        parts[3]="mach_o"
    #Rejoin new architecture
    arch = '-'.join(parts)
    return arch
