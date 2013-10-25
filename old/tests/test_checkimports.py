'''Unit test for CheckImport class'''

from mock import Mock
from textwrap import dedent
from twisted.trial import unittest

from scripts.checkimports import CheckImports


# pylint: disable=W0212
class TestCheckImports(unittest.TestCase):

    '''
    I test the CheckImport class against several well defined use case
    along with some real world code
    '''

    def setUp(self):
        '''
        I set up the checkimport and mock some of its methods we
        never want to execute
        '''
        self.patch(CheckImports, "printErrorMsg", Mock())
        self.checkImports = CheckImports()

    def testRegexImportValid(self):
        '''I test the 'import' regular expression'''
        data = dedent("""
            import os
            import sys
            import sqlachemy as sa
            import name_with_underscore
            import twisted.internet
            import_should_not_be_found = 1

              import with_indedent  # should NOT be found
            """).lstrip()
        lines = data.split("\n")
        self.assertEqual(self.checkImports._regexImport.match(lines[0]).group(1), "os")
        self.assertEqual(self.checkImports._regexImport.match(lines[1]).group(1), "sys")
        self.assertEqual(self.checkImports._regexImport.match(lines[2]).group(1), "sqlachemy as sa")
        self.assertEqual(self.checkImports._regexImport.match(lines[3]).group(1), "name_with_underscore")
        self.assertEqual(self.checkImports._regexImport.match(lines[4]).group(1), "twisted.internet")
        self.assertEqual(self.checkImports._regexImport.match(lines[5]), None)
        self.assertEqual(self.checkImports._regexImport.match(lines[6]), None)
        self.assertEqual(self.checkImports._regexImport.match(lines[7]), None)

    def testRegExpFromValid(self):
        '''I test the 'from/import' regular expression'''
        data = dedent("""
            from_should_not_be_found = 1
            from module import stuff, foo, bar
            from module.submodule import stuff
            """).lstrip()
        lines = data.split("\n")
        self.assertEqual(self.checkImports._regexFromImport.match(lines[0]), None)
        self.assertEqual(self.checkImports._regexFromImport.match(lines[1]).group(1), "module")
        self.assertEqual(self.checkImports._regexFromImport.match(lines[1]).group(2), "stuff, foo, bar")
        self.assertEqual(self.checkImports._regexFromImport.match(lines[2]).group(1), "module.submodule")
        self.assertEqual(self.checkImports._regexFromImport.match(lines[2]).group(2), "stuff")

    def testLineAnalyse(self):
        '''I test analyseLine method'''
        line = "import stuff; import other"
        self.assertFalse(self.checkImports.analyzeLine("filename", line, 0))

        line = "import stuff"
        self.assertTrue(self.checkImports.analyzeLine("filename", line, 0))

        line = "from stuff import module"
        self.assertTrue(self.checkImports.analyzeLine("filename", line, 0))

        line = "from stuff import module1, module2"
        self.assertFalse(self.checkImports.analyzeLine("filename", line, 0))

        line = "from stuff import (module1"
        self.assertFalse(self.checkImports.analyzeLine("filename", line, 0))

    def testLineOrderImport(self):
        '''I test the checkOrder method with 'import' statements alone'''
        data = dedent("""
            import sys
            import trace  # ordered
            import os  # bad place
            """).lstrip()
        lines = data.split("\n")
        self.assertTrue(self.checkImports.checkOrder("filename", lines[0], 1))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[1], 2))
        self.assertFalse(self.checkImports.checkOrder("filename", lines[2], 3))

    def testLineOrderFromImport1(self):
        '''I test the checkOrder method with 'from/import' statements alone'''
        data = dedent("""
            from module.submoduleA import foo
            from module.submoduleC import bar
            from module.submoduleB import bar
            """).lstrip()
        lines = data.split("\n")
        self.assertTrue(self.checkImports.checkOrder("filename", lines[0], 1))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[1], 2))
        self.assertFalse(self.checkImports.checkOrder("filename", lines[2], 3))

    def testLineOrderFromImport2(self):
        '''I test the checkOrder method with 'from/import' statement alone'''
        data = dedent("""
            from module.submoduleC import foo
            from module.submoduleA import bar
            from module.submoduleB import bar
            from module.submoduleD import bar
            """).lstrip()
        lines = data.split("\n")
        self.assertTrue(self.checkImports.checkOrder("filename", lines[0], 1))
        self.assertFalse(self.checkImports.checkOrder("filename", lines[1], 2))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[2], 3))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[3], 4))

    def testLineOrderFromImport3(self):
        '''I test the checkOrder method with 'from/import' statement alone'''
        data = dedent("""
            from module.submoduleA import bar
            from module.submoduleA import foo
            from module.submoduleA import anotherfoo
            """).lstrip()
        lines = data.split("\n")
        self.assertTrue(self.checkImports.checkOrder("filename", lines[0], 1))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[1], 2))
        self.assertFalse(self.checkImports.checkOrder("filename", lines[2], 3))

    def testLineOrderFromImport4(self):
        '''
        I test the checkOrder when import and from/import statements are
        mixed.
        '''
        data = dedent("""
            import stuff
            from module.submoduleA import bar
            from module.submoduleA import foo
            """).lstrip()
        lines = data.split("\n")
        self.assertTrue(self.checkImports.checkOrder("filename", lines[0], 1))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[1], 2))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[2], 3))

        self.assertEqual(self.checkImports.printErrorMsg.call_args_list[0][0],
                         ('filename', 2, "Warning: mixing of 'import ...' and "
                          "'from ... import ...' statements in the same group"))

    def testLineOrderFromImport5(self):
        '''I test unordered lines and verify there is only one error'''
        data = dedent("""
            from module.submoduleB import bbbb
            from module.submoduleA import aaa
            from module.submoduleC import cccccc
            """).lstrip()
        lines = data.split("\n")
        self.assertTrue(self.checkImports.checkOrder("filename", lines[0], 1))
        self.assertFalse(self.checkImports.checkOrder("filename", lines[1], 2))
        self.assertTrue(self.checkImports.checkOrder("filename", lines[2], 3))

    def testLineOrderFromImport6(self):
        '''I test unordered line and verify there is two errors'''
        data = dedent("""
            from module.submoduleC import cccccc
            from module.submoduleB import bbbb
            from module.submoduleA import aaa
            """).lstrip()
        lines = data.split("\n")
        self.assertTrue(self.checkImports.checkOrder("filename", lines[0], 1))
        self.assertFalse(self.checkImports.checkOrder("filename", lines[1], 2))
        self.assertFalse(self.checkImports.checkOrder("filename", lines[2], 3))

    def testGroupsOrderNominal(self):
        '''I test ordering with several groups'''
        data = dedent("""
            import os
            import sys

            import dictns
            import yetanotherdependency

            from cactus.step.somestep import stuff
            from cactus.step.somestep import yetanotherstuff
            """).lstrip()
        self.assertTrue(self.checkImports.checkData("filename", data))

    def testGroupsOrderNominal2(self):
        '''I test ordering with several other statements'''
        data = dedent("""
            import os
            import sys
            other_statement = 1
            """).lstrip()
        self.assertTrue(self.checkImports.checkData("filename", data))

    def testGroupsOrderFailure(self):
        '''I test unordered statements in the 3rd group'''
        data = dedent("""
            import os
            import sys

            import dictns
            import yetanotherdependency

            from cactus.step.somestep import yetanotherstuff
            from cactus.step.somestep import stuff  # bad order
            """).lstrip()
        self.assertFalse(self.checkImports.checkData("filename", data))

    def testGroupsOrderFailure2(self):
        '''I test unordered statements in the 2nd group'''
        data = dedent("""
            import os
            import sys

            import yetanotherdependency
            import dictns  # bad order

            from cactus.step.somestep import stuff
            from cactus.step.somestep import yetanotherstuff
            """).lstrip()
        self.assertFalse(self.checkImports.checkData("filename", data))

    def testGroupsOrderFailure3(self):
        '''
        I test import statement is well found to be 'unordered' when
        placed after ordered from/import
        '''
        data = dedent("""
            from cactus.step.somestep import stuff
            from cactus.step.somestep import yetanotherstuff
            import stuff
            """).lstrip()
        self.assertFalse(self.checkImports.checkData("filename", data))

    def testSortImportGroups(self):
        ''''
        I test sorting several not mixed goups
        '''
        data = dedent("""
            from cactus.step.somestep import bbb
            from cactus.step.somestep import aaaaa
            from cactus.step.somestep import ccc

            import jjjjjjj
            import iiiii

            from cactus.param.ffff import eeee
            from cactus.param.dddddd import gggggggg
            from cactus.param.aaaaa import aaaa

            def other_function():
                pass

            # This group should ALSO be sorted:
            from cactus.param.mmmmm import mmmm
            from cactus.param.kkkkk import kk

            # This group is already sorted:
            from cactus.param.tttt import ttt
            from cactus.param.uuu import uu
            from cactus.param.vvvvvv import vvvvv
            """).lstrip()
        result, processed_data = self.checkImports.sortImportGroups("filename", data)
        self.assertTrue(result)

        sorted_data = dedent("""
            from cactus.step.somestep import aaaaa
            from cactus.step.somestep import bbb
            from cactus.step.somestep import ccc

            import iiiii
            import jjjjjjj

            from cactus.param.aaaaa import aaaa
            from cactus.param.dddddd import gggggggg
            from cactus.param.ffff import eeee

            def other_function():
                pass

            # This group should ALSO be sorted:
            from cactus.param.kkkkk import kk
            from cactus.param.mmmmm import mmmm

            # This group is already sorted:
            from cactus.param.tttt import ttt
            from cactus.param.uuu import uu
            from cactus.param.vvvvvv import vvvvv
            """).lstrip()
        self.assertEqual(processed_data, sorted_data, "sort group failed")

    def testSortImportGroupsWithMixed(self):
        '''
        I test sorting of mixed group (import should be placed before
        from/import, and an empty line added
        '''
        data = dedent("""
            from cactus.step.somestep import bbb
            from cactus.step.somestep import aaaaa
            from cactus.step.somestep import ccc
            import jjjjjjj
            import iiiii
            """).lstrip()
        result, processed_data = self.checkImports.sortImportGroups("filename", data)
        self.assertTrue(result)
        sorted_data = dedent("""
            import iiiii
            import jjjjjjj

            from cactus.step.somestep import aaaaa
            from cactus.step.somestep import bbb
            from cactus.step.somestep import ccc
            """).lstrip()
        self.assertEqual(processed_data, sorted_data, "sort group failed")

    def testCompareImportLines(self):
        '''Unit test the line comparison method'''
        def asserter(line1, line2, expectedVal):
            '''shortcut for shorter lines'''
            self.assertEqual(self.checkImports.compareImportLines(line1, line2), expectedVal)
        asserter("import stuff1", "import stuff2", -1)
        asserter("import stuff2", "import stuff1", 1)
        asserter("from stuff1 import thing", "from stuff2 import thing", -1)
        asserter("from stuff2 import thing", "from stuff1 import thing", 1)
        asserter("from stuff2 import thing", "import stuff1", 1)
        asserter("import stuff1", "from stuff2 import thing", -1)
        asserter("import foo", "import foo", 0)

    def testCheckAndSortWithMixed(self):
        '''Real world processing with mixed import+from/import group'''
        data = dedent("""
            from twisted.internet import defer
            from buildbot.steps.master import MasterShellCommand
            from buildbot.status.results import SUCCESS, WARNINGS
            import time
            from txgerrit.txartifactory import artifactory, Artifactory
            from cactus.contracts.contracts import readProperties, createdProperties, updatedProperties
            from cactus.steps.step_utils import StepUtilMixin


            class MetabuilderMetadata(object):
                # we therefore just store the branch and metabuilder
                # from the artifact path for now
                path = metabuilderPath[metabuilderPath.index(repoSlash) + len(repoSlash):]
                branchbuilder, num = path.split("/")
                branch, buildername = branchbuilder.split("-")
                self.branch = branch
                self.buildername = buildername
                self.buildnumber = num
                self.path = metabuilderPath
                self.createdDate = Artifactory.internetDateTimeToSecondsSinceEpoch(artifact.created)
                self.currTime = currTime

            def shouldBeDeleted(self, p):
                res = True
                if p.branch:
                    res = res and self.branch == p.branch
                if p.buildername:
                    res = res and self.buildername == p.buildername
                res = res and self.createdDate < self.currTime - p.age_threshold
                return res
            """).lstrip()
        sorted_data = dedent("""
            import time

            from buildbot.status.results import SUCCESS
            from buildbot.status.results import WARNINGS
            from buildbot.steps.master import MasterShellCommand
            from cactus.contracts.contracts import createdProperties
            from cactus.contracts.contracts import readProperties
            from cactus.contracts.contracts import updatedProperties
            from cactus.steps.step_utils import StepUtilMixin
            from twisted.internet import defer
            from txgerrit.txartifactory import Artifactory
            from txgerrit.txartifactory import artifactory


            class MetabuilderMetadata(object):
                # we therefore just store the branch and metabuilder
                # from the artifact path for now
                path = metabuilderPath[metabuilderPath.index(repoSlash) + len(repoSlash):]
                branchbuilder, num = path.split("/")
                branch, buildername = branchbuilder.split("-")
                self.branch = branch
                self.buildername = buildername
                self.buildnumber = num
                self.path = metabuilderPath
                self.createdDate = Artifactory.internetDateTimeToSecondsSinceEpoch(artifact.created)
                self.currTime = currTime

            def shouldBeDeleted(self, p):
                res = True
                if p.branch:
                    res = res and self.branch == p.branch
                if p.buildername:
                    res = res and self.buildername == p.buildername
                res = res and self.createdDate < self.currTime - p.age_threshold
                return res
            """).lstrip()
        res, processed_data = self.checkImports.sortImportGroups("filename", data)
        self.assertEqual(res, True)
        self.assertEqual(processed_data, sorted_data)
        self.assertEqual(self.checkImports.printErrorMsg.call_args_list[0][0],
                         ('filename', 1,
                          "Bad order for this import"))
        self.assertEqual(self.checkImports.printErrorMsg.call_args_list[1][0],
                         ('filename', 2,
                          "multiple module imported on one line. Please import "
                          "each module on a single line."))
        self.assertEqual(self.checkImports.printErrorMsg.call_args_list[2][0],
                         ('filename', 2,
                          "Bad order for this import"))
        self.assertEqual(self.checkImports.printErrorMsg.call_args_list[3][0],
                         ('filename', 3,
                          "Warning: mixing of 'import ...' and 'from ... import ...' "
                          "statements in the same group"))

    def testCheckAndSortNominal(self):
        '''Real world sort (splitting group)'''
        data = dedent("""
            import time

            from twisted.internet import defer

            from buildbot.steps.master import MasterShellCommand
            from buildbot.status.results import WARNINGS,  SUCCESS

            from txgerrit.txartifactory import artifactory
            from txgerrit.txartifactory import Artifactory

            from cactus.contracts.contracts import readProperties
            from cactus.contracts.contracts import updatedProperties
            from cactus.steps.step_utils import StepUtilMixin
            from cactus.contracts.contracts import createdProperties


            class MetabuilderMetadata(object):
                # we therefore just store the branch and metabuilder
                # from the artifact path for now
                path = metabuilderPath[metabuilderPath.index(repoSlash) + len(repoSlash):]
                branchbuilder, num = path.split("/")
                branch, buildername = branchbuilder.split("-")
                self.branch = branch
                self.buildername = buildername
                self.buildnumber = num
                self.path = metabuilderPath
                self.createdDate = Artifactory.internetDateTimeToSecondsSinceEpoch(artifact.created)
                self.currTime = currTime

            def shouldBeDeleted(self, p):
                res = True
                if p.branch:
                    res = res and self.branch == p.branch
                if p.buildername:
                    res = res and self.buildername == p.buildername
                res = res and self.createdDate < self.currTime - p.age_threshold
                return res
            """).lstrip()
        sorted_data = dedent("""
            import time

            from twisted.internet import defer

            from buildbot.status.results import SUCCESS
            from buildbot.status.results import WARNINGS
            from buildbot.steps.master import MasterShellCommand

            from txgerrit.txartifactory import Artifactory
            from txgerrit.txartifactory import artifactory

            from cactus.contracts.contracts import createdProperties
            from cactus.contracts.contracts import readProperties
            from cactus.contracts.contracts import updatedProperties
            from cactus.steps.step_utils import StepUtilMixin


            class MetabuilderMetadata(object):
                # we therefore just store the branch and metabuilder
                # from the artifact path for now
                path = metabuilderPath[metabuilderPath.index(repoSlash) + len(repoSlash):]
                branchbuilder, num = path.split("/")
                branch, buildername = branchbuilder.split("-")
                self.branch = branch
                self.buildername = buildername
                self.buildnumber = num
                self.path = metabuilderPath
                self.createdDate = Artifactory.internetDateTimeToSecondsSinceEpoch(artifact.created)
                self.currTime = currTime

            def shouldBeDeleted(self, p):
                res = True
                if p.branch:
                    res = res and self.branch == p.branch
                if p.buildername:
                    res = res and self.buildername == p.buildername
                res = res and self.createdDate < self.currTime - p.age_threshold
                return res
            """).lstrip()
        res, processed_data = self.checkImports.sortImportGroups("filename", data)
        self.assertEqual(res, True)
        self.assertEqual(processed_data, sorted_data)

    def testCheckAndSortNominal2(self):
        '''Real world with splitting and mixing group reordering'''
        data = dedent("""
            from buildbot.config import BuilderConfig
            from buildbot.process import factory
            from buildbot.process.properties import WithProperties
            from buildbot.process.properties import renderer
            from buildbot.schedulers.forcesched import BooleanParameter
            from buildbot.schedulers.forcesched import DynamicChoiceStringParameter, ChoiceStringParameter, InheritBuildParameter
            import os
            from buildbot.schedulers.forcesched import FixedParameter
            from buildbot.schedulers.forcesched import ForceScheduler
            from buildbot.schedulers.forcesched import StringParameter
            from buildbot.schedulers.triggerable import Triggerable
            from buildbot.status.builder import SUCCESS
            from buildbot.status.builder import WARNINGS
            from buildbot.steps.shell import Compile
            from buildbot.steps.trigger import Trigger

            from txgerrit.change_utils import NO_REORDERING
            from txgerrit.change_utils import DOWNLOAD_ORDERING_MODES
            from txgerrit.change_utils import REORDER_WITHOUT_DOWNLOADING_DEPS

            from cactus.builderfactories.autolint import acsAutolintFactory
            from cactus.builderfactories.autolint import doNotCheckBugzilla
            from cactus.builderfactories.builder_factory import BuilderFactory
            from cactus.builderfactories.builderfactories import CommonFactory
            from cactus.builderfactories.builderfactories import MicroBuildFactory
            from cactus.builderfactories.factory_utils import isVariantRelatedToMerge
            from cactus.builderfactories.metabuild_factories import parameterizedMetabuildFactory
            from cactus.cfg.utils import strip
            from cactus.parameters.changeids_param import ChangeIDsParameter
            from cactus.schedulers.groupedmergescheduler import makeGroupedMergeScheduler
            from cactus.schedulers.utils import branch_scheduler_name
            from cactus.schedulers.utils import unit_test_scheduler_name
            from cactus.steps.create_virtualenv import VirtualenvSetup
            from cactus.steps.run_test import RunTest as RunTestTR
            from cactus.steps.run_test import ACS_CI_UNIT_TEST_PROFILE
            from cactus.steps.scheduling_utils import acs_lock
            from cactus.steps.scheduling_utils import myNextAcsBuildSlave
            from cactus.steps.scheduling_utils import myNextAcsUnitTestSlave
            from cactus.steps.scheduling_utils import neverMerge
            from cactus.steps.scheduling_utils import slave_lock
            from cactus.steps.trigger_steps import get_unit_test_campaigns_for_variant
            from cactus.steps.trigger_steps import TriggerACSForACS
            from cactus.steps.trigger_steps import TriggerACSUnitTests
            from cactus.steps.trigger_steps import TriggerTestACS
            from cactus.steps.weekly_steps import CleaningBranch


            build_acs_builder_name = "build-acs"
            acs_unit_test_buildername = "acs_unit_tests"
            """).rstrip()
        sorted_data = dedent("""
            import os

            from buildbot.config import BuilderConfig
            from buildbot.process import factory
            from buildbot.process.properties import WithProperties
            from buildbot.process.properties import renderer
            from buildbot.schedulers.forcesched import BooleanParameter
            from buildbot.schedulers.forcesched import ChoiceStringParameter
            from buildbot.schedulers.forcesched import DynamicChoiceStringParameter
            from buildbot.schedulers.forcesched import FixedParameter
            from buildbot.schedulers.forcesched import ForceScheduler
            from buildbot.schedulers.forcesched import InheritBuildParameter
            from buildbot.schedulers.forcesched import StringParameter
            from buildbot.schedulers.triggerable import Triggerable
            from buildbot.status.builder import SUCCESS
            from buildbot.status.builder import WARNINGS
            from buildbot.steps.shell import Compile
            from buildbot.steps.trigger import Trigger

            from txgerrit.change_utils import DOWNLOAD_ORDERING_MODES
            from txgerrit.change_utils import NO_REORDERING
            from txgerrit.change_utils import REORDER_WITHOUT_DOWNLOADING_DEPS

            from cactus.builderfactories.autolint import acsAutolintFactory
            from cactus.builderfactories.autolint import doNotCheckBugzilla
            from cactus.builderfactories.builder_factory import BuilderFactory
            from cactus.builderfactories.builderfactories import CommonFactory
            from cactus.builderfactories.builderfactories import MicroBuildFactory
            from cactus.builderfactories.factory_utils import isVariantRelatedToMerge
            from cactus.builderfactories.metabuild_factories import parameterizedMetabuildFactory
            from cactus.cfg.utils import strip
            from cactus.parameters.changeids_param import ChangeIDsParameter
            from cactus.schedulers.groupedmergescheduler import makeGroupedMergeScheduler
            from cactus.schedulers.utils import branch_scheduler_name
            from cactus.schedulers.utils import unit_test_scheduler_name
            from cactus.steps.create_virtualenv import VirtualenvSetup
            from cactus.steps.run_test import ACS_CI_UNIT_TEST_PROFILE
            from cactus.steps.run_test import RunTest as RunTestTR
            from cactus.steps.scheduling_utils import acs_lock
            from cactus.steps.scheduling_utils import myNextAcsBuildSlave
            from cactus.steps.scheduling_utils import myNextAcsUnitTestSlave
            from cactus.steps.scheduling_utils import neverMerge
            from cactus.steps.scheduling_utils import slave_lock
            from cactus.steps.trigger_steps import TriggerACSForACS
            from cactus.steps.trigger_steps import TriggerACSUnitTests
            from cactus.steps.trigger_steps import TriggerTestACS
            from cactus.steps.trigger_steps import get_unit_test_campaigns_for_variant
            from cactus.steps.weekly_steps import CleaningBranch


            build_acs_builder_name = "build-acs"
            acs_unit_test_buildername = "acs_unit_tests"
            """).rstrip()
        res, processed_data = self.checkImports.sortImportGroups("filename", data)
        self.assertEqual(res, True)
        self.assertEqual(processed_data, sorted_data)

    def testSortAndSplit(self):
        '''Test split and sort a single group'''
        data = dedent("""
            from cactus.steps.otherstep import stuff
            from cactus.steps.thestep import step3, step2, step1
            from cactus.steps.anotherstep import anotherstuff
            """).rstrip()
        splitted_date = dedent("""
            from cactus.steps.anotherstep import anotherstuff
            from cactus.steps.otherstep import stuff
            from cactus.steps.thestep import step1
            from cactus.steps.thestep import step2
            from cactus.steps.thestep import step3
            """).rstrip()
        res, processed_data = self.checkImports.sortImportGroups("filename", data)
        self.assertEqual(res, True)

        self.assertEqual(processed_data, splitted_date)
