# vim: set fileencoding=utf-8 :
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

import hashlib
import unittest
import re


def validateTagVersion(version):
    for i in version:
        if not i.isalnum():
            if not ((i == "_") or (i == ".")):
                return False
    return True


def validateTag(tag):
    if len(tag) == 0:
        return False
    lst = tag.split(':')
    if len(lst) > 2:
        return False  # More than one version component is not allowed
    for i in lst[0]:
        if not i.isalnum():
            if i != "_":
                return False
    if len(lst) > 1:
        return validateTagVersion(lst[1])
    return True


class SoftwareTag:
    def __init__(self, tag):
        """ Takes tag and parses it. If it can't parse - raises exception of invalid value
        :type tag: str
        """
        if not ((type(tag) == str) or (type(tag) == unicode)):
            raise (BaseException("Invalid input data-type"))
        if not validateTag(tag):
            raise (BaseException("Malformed tag"))
        tag_version = tag.split(':')
        self.tag = tag_version[0].lower()  # No, this should be lowercase
        self.version = None if len(tag_version) == 1 else tag_version[1]

    def __repr__(self):
        return "SoftwareTag()"

    def __str__(self):
        if self.version:
            return "%s:%s" % (self.tag, self.version)
        else:
            return self.tag

    def has_version(self):
        return self.version is not None

    def match(self, tag):  # self is "on server", tag is "request"
        if self.tag == tag.tag:
            # Names are the same, that is good, matching versions now.
            if self.version == tag.version:
                return True
            else:
                if tag.version is None:
                    return True  # qt in request, anything else on server - True
                if self.version is not None and self.version.startswith(tag.version + "."):
                    return True
                return False
        return False

    def make_regex(self):
        if self.version is None:
            # versionless tag
            temp_string = re.escape(self.tag)
            regex = "(%s:[a-z0-9_.]*)|(%s)" % (temp_string, temp_string,)
        else:
            # tag with versions
            temp_string = re.escape("%s:%s" % (self.tag, self.version))
            regex = "(%s\.[a-z0-9_.]*)|(%s)" % (temp_string, temp_string)
        return regex


class SoftwareTagList:
    def __init__(self):
        # dictionary of tags, key is - tag name
        self.taglist = dict()

    def __str__(self):
        lst = list()
        for key, value in self.taglist.items():
            lst += [str(i) for i in value]
        lst.sort()
        return ",".join(lst)

    def __repr__(self):
        return "SoftwareTagList()"

    def __getitem__(self, item):
        return self.taglist[item]

    def parse(self, tag_string):
        self.taglist = dict()
        try:
            return all(self.append(SoftwareTag(i)) for i in tag_string.split(','))
        except:
            return False

    def has_version(self, tag_name):
        if tag_name in self.taglist:
            # This check is possible, because, when there is tag without version - it is the only tag in the list
            if self.taglist[tag_name][0].has_version():
                return True
        return False

    def append(self, tag):
        # tag should be SoftwareTag, return false or raise exception in case it is not so
        if tag.has_version():
            if tag.tag in self.taglist:
                # Tag in list - need to check version
                if self.has_version(tag.tag) and not any(tag.match(i) for i in self.taglist[tag.tag]):
                    self.taglist[tag.tag].append(tag)
                    self.taglist[tag.tag].sort()  # this is slow, I guess
            else:
                # Tag not in list - just add it.
                self.taglist[tag.tag] = [tag, ]
        else:
            # tag without version tag
            self.taglist[tag.tag] = [tag, ]
        return True

    def is_empty(self):
        return len(self.taglist) == 0

    def make_regex(self):
        lst = list()
        for key, value in self.taglist.items():
            regex = "(^|,)%s(,|$)" % "|".join([i.make_regex() for i in value])
            lst.append(regex)
        return lst

    def match_positive(self, taglist):
        # checks that everything from tag list matches current tags
        # Start checking with checking if all requested tags in taglist are present in self.taglist
        for i in taglist.taglist:
            if i not in self.taglist:
                return False
        # Now we need to check if versions are matching
        for tag in taglist.taglist:
            if not self.has_version(tag):
                # If package tag accepts anything - it already matches, next please
                continue
            if taglist.has_version(tag) and not any(v1.match(v) for v in taglist[tag] for v1 in self[tag]):
                return False
        return True

    def match_negative(self, taglist):
        # checks that nothing from taglist matches current tags
        for i in taglist.taglist:
            if i in self.taglist:
                if (not taglist.has_version(i)) or (not self.has_version(i)):
                    return False
                # Tag found, version list is present. check if it matches, if it does - check is failed
                for version in taglist[i]:
                    for version1 in self[i]:
                        if version1.match(version):
                            return False
        return True

    def hash(self):
        # Looks like the list is sorted, but well...
        return hashlib.md5(str(self)).hexdigest()


class TestSoftwareTagMethods(unittest.TestCase):
    def test_tag_creation(self):
        tag = SoftwareTag('qt')
        self.assertFalse(tag.has_version())
        tag = SoftwareTag('qt:5.01')
        self.assertTrue(tag.has_version())
        tag = SoftwareTag('qt:5.01_asdf_the_version')
        self.assertTrue(tag.has_version())
        tag = SoftwareTag('Qt')
        self.assertFalse(tag.has_version())
        with self.assertRaisesRegexp(BaseException, "Malformed tag"):
            SoftwareTag('фыва')
        with self.assertRaisesRegexp(BaseException, "Malformed tag"):
            SoftwareTag('фыва:5.1')
        with self.assertRaisesRegexp(BaseException, "Malformed tag"):
            SoftwareTag('qt.1:5.1')
        with self.assertRaisesRegexp(BaseException, "Invalid input data-type"):
            SoftwareTag(1)

    def test_tag_match(self):
        tag_13 = SoftwareTag('qt:1.3')
        tag_12 = SoftwareTag('qt:1.2')
        tag_121 = SoftwareTag('qt:1.2.1')
        tag_122 = SoftwareTag('qt:1.2.2')
        tag = SoftwareTag('qt')
        tag2 = SoftwareTag('neptune')
        self.assertFalse(tag_12.match(tag_13))
        self.assertFalse(tag_13.match(tag_12))
        self.assertTrue(tag_121.match(tag_12))
        self.assertTrue(tag_122.match(tag_12))
        self.assertTrue(tag_121.match(tag_121))
        self.assertFalse(tag_12.match(tag_121))
        self.assertFalse(tag.match(tag2))
        self.assertTrue(tag_13.match(tag))
        self.assertFalse(tag.match(tag_13))


class TestSoftwareTagListMethods(unittest.TestCase):
    def test_empty(self):
        lst = SoftwareTagList()
        self.assertTrue(lst.is_empty())

    def test_not_empty_after_append(self):
        lst = SoftwareTagList()
        lst.append(SoftwareTag('qt'))
        self.assertFalse(lst.is_empty())

    def test_empty_matches_everything(self):
        empty_list = SoftwareTagList()
        test_list = SoftwareTagList()
        test_list.append(SoftwareTag('qt'))
        self.assertTrue(test_list.match_positive(empty_list))
        self.assertTrue(test_list.match_negative(empty_list))

    def test_match_positive(self):
        list_to_test = SoftwareTagList()
        list_to_test.parse("qt:5.1,neptune,test:1,second_test")
        matching_list = SoftwareTagList()
        matching_list.parse("qt")
        self.assertTrue(list_to_test.match_positive(matching_list))
        matching_list.parse("qt:5.1")
        self.assertTrue(list_to_test.match_positive(matching_list))
        matching_list.parse("qt:5.1,qt:5.2,neptune:1")
        self.assertTrue(list_to_test.match_positive(matching_list))
        matching_list.parse("qt:5.1,test:2")
        self.assertFalse(list_to_test.match_positive(matching_list))
        matching_list.parse("qt:5.1.1")
        self.assertFalse(list_to_test.match_positive(matching_list))

    def test_match_negative(self):
        list_to_test = SoftwareTagList()
        list_to_test.parse("qt:5.1,neptune")
        matching_list = SoftwareTagList()
        matching_list.parse("qt")
        self.assertFalse(list_to_test.match_negative(matching_list))
        matching_list.parse("qt:5.1")
        self.assertFalse(list_to_test.match_negative(matching_list))
        matching_list.parse("qt:5.1,qt:5.2,neptune:1")
        self.assertFalse(list_to_test.match_negative(matching_list))
        matching_list.parse("qt:5.1,qt:5.2")
        self.assertFalse(list_to_test.match_negative(matching_list))
        matching_list.parse("test")
        self.assertTrue(list_to_test.match_negative(matching_list))

    def test_append_invalid(self):
        lst = SoftwareTagList()
        with self.assertRaisesRegexp(BaseException, "Malformed tag"):
            self.assertFalse(lst.append(SoftwareTag('qt:1:1')))  # Invalid version
        with self.assertRaisesRegexp(BaseException, "Malformed tag"):
            self.assertFalse(lst.append(SoftwareTag('фыва')))  # Non-ascii
        with self.assertRaisesRegexp(BaseException, "Malformed tag"):
            self.assertFalse(lst.append(SoftwareTag('')))  # empty tag is not valid

    def test_append_valid(self):
        lst = SoftwareTagList()
        # capital letters should be treated as lowercase
        self.assertTrue(lst.append(SoftwareTag('QT')))
        # underscore is allowed, capital letters should be treated as lowercase
        self.assertTrue(lst.append(SoftwareTag('QT_something')))
        # Version is valid, tag is valid too
        self.assertTrue(lst.append(SoftwareTag('qt:1.1.1')))

    def test_parsing_positive(self):
        lst = SoftwareTagList()
        self.assertTrue(lst.parse('qt'))
        self.assertTrue(lst.parse('qt:5'))
        self.assertTrue(lst.parse('qt:5.1'))
        self.assertTrue(lst.parse('qt:5.1,qt:5.2'))
        self.assertTrue(lst.parse('qt:5.1,qt:5.2,neptune'))
        self.assertTrue(lst.parse('qt:5.1,qt:5.2,neptune:5.1,neptune:5.2'))
        # This should equal to qt:5.1,qt:5.2,neptune:5.1,neptune:5.2 - due to matching
        self.assertTrue(lst.parse('qt:5.1,qt:5.2,qt:5.2,qt:5.2.1,neptune:5.1,neptune:5.2'))
        # This equals to: qt, neptune, due to matching
        self.assertTrue(lst.parse('qt,qt:5.2,neptune:5.1,neptune'))

    def test_parsing_negative(self):
        lst = SoftwareTagList()
        self.assertFalse(lst.parse(',,'))  # empty tags
        self.assertFalse(lst.parse('фыва'))  # non-ascii
        self.assertFalse(lst.parse('qt:5.1:5.2,qt'))  # multiple versions

    def test_hashes_does_not_depend_on_order(self):
        lst1 = SoftwareTagList()
        lst2 = SoftwareTagList()
        self.assertTrue(lst1.parse('qt:5,qt:4,neptune:1'))
        self.assertTrue(lst2.parse('neptune:1,qt:4,qt:5'))
        self.assertEqual(lst1.hash(), lst2.hash())

    def test_different_list_different_hash(self):
        lst1 = SoftwareTagList()
        lst2 = SoftwareTagList()
        self.assertTrue(lst1.parse('qt:5,neptune:2'))
        self.assertTrue(lst2.parse('neptune:1,qt:5'))
        self.assertNotEqual(lst1.hash(), lst2.hash())


if __name__ == '__main__':
    unittest.main()
