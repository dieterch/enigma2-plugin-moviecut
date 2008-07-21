from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
import Screens.Standby
from Components.config import *
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.Button import Button
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import eTimer, eServiceReference, eServiceCenter, iServiceInformation, eConsoleAppContainer
from os import access, chmod, X_OK

mcut_path = "/usr/lib/enigma2/python/Plugins/Extensions/MovieCut/bin/mcut"
# Hack to make sure it is executable
if not access(mcut_path, X_OK):
	chmod(mcut_path, 493)

def main(session, service, **kwargs):
	session.open(MovieCut, service, **kwargs)

def Plugins(**kwargs):
	return PluginDescriptor(name="MovieCut", description="Execute cuts...", where = PluginDescriptor.WHERE_MOVIELIST, fnc=main)


class MovieCut(ChoiceBox):
	def __init__(self, session, service):
		self.service = service
		serviceHandler = eServiceCenter.getInstance()
		path = self.service.getPath()
		info = serviceHandler.info(self.service)
		if not info:
			self.name = path
		else:
			self.name = info.getName(self.service)
		tlist = []
		tlist.append(("Don't cut", "CALLFUNC", self.confirmed0))
		tlist.append(("Replace the original movie with the cut movie", "CALLFUNC", self.confirmed1))
		tlist.append(("Place the cut movie in a new file ending with \" cut\"", "CALLFUNC", self.confirmed2))
		tlist.append(("Advanced cut parameter settings...", "CALLFUNC", self.confirmed3))
		ChoiceBox.__init__(self, session, _("How would you like to cut \"%s\"?") % (self.name), list = tlist, selection = 0)
		self.skinName = "ChoiceBox"

	def confirmed0(self, arg):
		self.close()

	def confirmed1(self, arg):
		MovieCutSpawn(self.session, self, [mcut_path, "-r", self.service.getPath()], self.name)

	def confirmed2(self, arg):
		MovieCutSpawn(self.session, self, [mcut_path, self.service.getPath()], self.name)

	def confirmed3(self, arg):
		serviceHandler = eServiceCenter.getInstance()
		info = serviceHandler.info(self.service)
		self.path = self.service.getPath()
		self.name = info.getName(self.service)
		self.descr = info.getInfoString(self.service, iServiceInformation.sDescription)
		self.session.openWithCallback(self.advcutConfirmed, AdvancedCutInput, self.name, self.path, self.descr)

	def advcutConfirmed(self, ret):
		if len(ret) <= 1 or not ret[0]:
			self.close()
			return
		clist = [mcut_path]
		if ret[1] == True:
			clist.append("-r")
		clist.append(self.service.getPath())
		if ret[2] != False:
			clist += ["-o", ret[2]]
		if ret[3] != False:
			clist += ["-n", ret[3]]
		if ret[4] != False:
			clist += ["-d", ret[4]]
		if ret[5] != False:
			clist.append("-c")
			clist += ret[5]
		MovieCutSpawn(self.session, self, clist, self.name)
		
class AdvancedCutInput(Screen, ConfigListScreen):
	skin = """
	<screen name="AdvancedCutInput" position="80,100" size="550,320" title="Cut Parameter Input">
		<widget name="config" position="5,10" size="530,250" />
		<widget name="ok" position="90,265" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" />
		<widget name="oktext" position="90,265" size="140,40" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1" />
		<widget name="cancel" position="320,265" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" />
		<widget name="canceltext" position="320,265" size="140,40" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1" />
	</screen>"""

	def __init__(self, session, name, path, descr):
		self.skin = AdvancedCutInput.skin
		Screen.__init__(self, session)

		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()

		if self.baseName(path) == self.baseName(name):
			self.title = ""
		else:
			self.title = name
		self.dir = self.dirName(path)
		self.file = self.baseName(path) + " cut"
		self.descr = descr
		self.input_replace = ConfigSelection(choices = [("no", _("No")), ("yes", _("Yes"))], default = "no")
		self.input_file = ConfigText(default = self.file, fixed_size = False, visible_width = 45)
		self.input_title = ConfigText(default = self.title, fixed_size = False, visible_width = 45)
		self.input_descr = ConfigText(default = self.descr, fixed_size = False, visible_width = 45)
		tmp = config.movielist.videodirs.value
		if not self.dir in tmp:
			tmp.append(self.dir)
		self.input_dir = ConfigSelection(choices = tmp, default = self.dir)
		self.input_manual = ConfigSelection(choices = [("no", _("Cutlist")), ("yes", _("Manual specification"))], default = "no")
		self.input_space = ConfigNothing()
		self.input_manualcuts = ConfigText(default = "", fixed_size = False)
		self.input_manualcuts.setUseableChars(" 0123456789:.")
		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keySelectOrGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.entry_replace = getConfigListEntry(_("Replace original:"), self.input_replace)
		self.entry_file = getConfigListEntry(_("New filename:"), self.input_file)
		self.entry_title = getConfigListEntry(_("New title:"), self.input_title)
		self.entry_descr = getConfigListEntry(_("New description:"), self.input_descr)
		self.entry_dir = getConfigListEntry(_("New location:"), self.input_dir)
		self.entry_manual = getConfigListEntry(_("Cut source:"), self.input_manual)
		self.entry_space = getConfigListEntry(_("Cuts (an IN OUT IN OUT ... sequence of hour:min:sec)"), self.input_space)
		self.entry_manualcuts = getConfigListEntry(_(":"), self.input_manualcuts)
		self.createSetup(self["config"])

	def createSetup(self, configlist):
		self.list = []
		self.list.append(self.entry_replace)
		if self.input_replace.value == "no":
			self.list.append(self.entry_file)
			self.list.append(self.entry_dir)
		self.list.append(self.entry_title)
		self.list.append(self.entry_descr)
		self.list.append(self.entry_manual)
		if self.input_manual.value == "yes":
			self.list.append(self.entry_space)
			self.list.append(self.entry_manualcuts)
		configlist.list = self.list
		configlist.l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		cc = self["config"].getCurrent()
		if cc is self.entry_replace or cc is self.entry_manual:
			self.createSetup(self["config"])

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		cc = self["config"].getCurrent()
		if cc is self.entry_replace or cc is self.entry_manual:
			self.createSetup(self["config"])

	def pathSelected(self, res):
		if res is not None:
			if config.movielist.videodirs.value != self.input_dir.choices:
				self.input_dir.setChoices(config.movielist.videodirs.value, default=res)
			self.input_dir.value = res

	def keySelectOrGo(self):
		if self["config"].getCurrent() == self.entry_dir:
			self.session.openWithCallback(
				self.pathSelected,
				MovieLocationBox,
				_("Choose target folder"),
				self.input_dir.value,
			)
		else:
			self.keyGo()

	def keyGo(self):
		if self.input_replace.value == "yes":
			path = False
		else:
			path = self.rejoinName(self.input_dir.value, self.input_file.value)
		if self.input_manual.value == "no":
			cuts = False
		else:
			cuts = self.input_manualcuts.value.split(' ')
			while "" in cuts:
				cuts.remove("")
		self.close((True, self.input_replace.value, path, self.input_title.value, self.input_descr.value, cuts))

	def keyCancel(self):
		self.close((False,))

	def baseName(self, str):
		name = str.split('/')[-1]
		if name.endswith(".ts") is True:
			return name[:-3]
		else:
			return name

	def dirName(self, str):
		return '/'.join(str.split('/')[:-1]) + '/'

	def rejoinName(self, dir, name):
		name = name.strip()
		if name.endswith(".ts") is True:
			return dir + name[:-3]
		else:
			return dir + name

class MovieCutQueue:
	def __init__(self):
		self.container = eConsoleAppContainer()
		self.container.appClosed.get().append(self.runDone)
		self.queue = []
		self.running = False

	def enqueue(self, cb, cmd):
		self.queue.append((cb, cmd))
		if not self.running:
			self.running = True
			self.runNext()
			return True
		else:
			return False

	def runNext(self):
		if not self.queue:
			self.running = False
		else:
			self.container.execute(self.queue[0][1][0], self.queue[0][1])

	def runDone(self, retval):
		cb = self.queue[0][0]
		self.queue = self.queue[1:]
		cb(retval)
		self.runNext()

global_mcut_errors = ["The movie \"%s\" is successfully cut",
		      "Cutting failed for movie \"%s\":\nBad arguments",
		      "Cutting failed for movie \"%s\":\nCouldn't open input .ts file",
		      "Cutting failed for movie \"%s\":\nCouldn't open input .cuts file",
		      "Cutting failed for movie \"%s\":\nCouldn't open input .ap file",
		      "Cutting failed for movie \"%s\":\nCouldn't open output .ts file",
		      "Cutting failed for movie \"%s\":\nCouldn't open output .cuts file",
		      "Cutting failed for movie \"%s\":\nCouldn't open output .ap file",
		      "Cutting failed for movie \"%s\":\nEmpty .ap file",
		      "Cutting failed for movie \"%s\":\nNo cuts specified",
		      "Cutting failed for movie \"%s\":\nRead/write error (disk full?)",
		      "Cutting was aborted for movie \"%s\""]

global_mcut_queue = MovieCutQueue()

global_mcut_block = False

class MovieCutSpawn:
	def __init__(self, session, parent, clist, name):
		global global_mcut_queue
		global global_mcut_block
		self.session = session
		self.parent = parent
		self.name = name
		self.clist = clist
		self.mess = ""
		self.dialog = False
		self.waitTimer = eTimer()
		self.waitTimer.callback.append(self.doWaitAck)
		if global_mcut_queue.enqueue(self.doAck, clist):
			mess = _("The movie \"%s\" is cut in the background.") % (self.name)
		else:
			mess = _("Another movie is currently cut.\nThe movie \"%s\" will be cut in the background after it.") % (self.name)
		global_mcut_block = True
		self.dialog = self.session.openWithCallback(self.endc, MessageBox, mess, MessageBox.TYPE_INFO)

	def doAck(self, retval):
		global global_mcut_errors
#		if WIFEXITED(retval):
#			self.mess = global_mcut_errors[WEXITSTATUS(retval)] % (self.name)
#		else:
#			self.mess = global_mcut_errors[-1] % (self.name)
		self.mess = global_mcut_errors[retval] % (self.name)
		self.doWaitAck()

	def doWaitAck(self):
		global global_mcut_block
		if Screens.Standby.inStandby or not self.session.in_exec or (global_mcut_block and not self.dialog):
			self.waitTimer.start(2000, True)
		else:
			global_mcut_block = True
			self.session.openWithCallback(self.endw, MessageBox, self.mess, MessageBox.TYPE_INFO)

	def endw(self, arg = 0):
		global global_mcut_block
		global_mcut_block = False
		if self.session.current_dialog == self.dialog:
			self.session.current_dialog.close(True)
			self.endc(arg)

	def endc(self, arg = 0):
		global global_mcut_block
		global_mcut_block = False
		self.dialog = False
		self.parent.close()
#		self.session.current_dialog.close()
