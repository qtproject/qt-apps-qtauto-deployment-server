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

def getOsArch(str):
    os = None
    arch = None
    fmt = None
    if str.startswith("ELF "):
        os = "Linux"
        arch = str.split(',')
        arch = arch[1]
        fmt = "elf"
    elif str.startswith("Mach-O "):
        os = "macOS"
        if " universal " in str:
            # Universal binary - not supported
            raise Exception("Universal binaries are not supported in packages")
        else:
            arch = str.split(' ')
            arch = arch[2]
            fmt = "mach_o"
    elif str.startswith("PE32+ ") or str.startswith("PE32 "):
        os = "Windows"
        arch = str.split(',')
        arch = arch[0]  # Take first part
        arch = arch.split(' ')
        arch = arch[-1]  # Take last element
        fmt = "pe32"
    if arch:
        arch = arch.replace('_', '-')
    result = {'os': os, 'arch': arch, 'format': fmt }
    if os:
        return result
    else:
        return None
