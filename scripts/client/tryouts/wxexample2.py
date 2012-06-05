import wx
import os
import sys

try:
    dirName = os.path.dirname(os.path.abspath(__file__))
except:
    dirName = os.path.dirname(os.path.abspath(sys.argv[0]))

sys.path.append(os.path.split(dirName)[0])

try:
    from agw import buttonpanel as bp
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.buttonpanel as bp

import images
import random

#----------------------------------------------------------------------

ID_BackgroundColour = wx.NewId()
ID_GradientFrom = wx.NewId()
ID_GradientTo = wx.NewId()
ID_BorderColour = wx.NewId()
ID_CaptionColour = wx.NewId()
ID_ButtonTextColour = wx.NewId()
ID_SelectionBrush = wx.NewId()
ID_SelectionPen = wx.NewId()
ID_SeparatorColour = wx.NewId()




class ButtonPanelDemo(wx.Frame):

    def __init__(self, parent, id=wx.ID_ANY, title="ButtonPanel wxPython Demo ;-)",
                 pos=wx.DefaultPosition, size=(640, 400), style=wx.DEFAULT_FRAME_STYLE):

        wx.Frame.__init__(self, parent, id, title, pos, size, style)

        self.useredited = False
        self.hassettingpanel = False

        self.SetIcon(images.Mondrian.GetIcon())
        self.CreateMenuBar()

        self.statusbar = self.CreateStatusBar(2, wx.ST_SIZEGRIP)
        self.statusbar.SetStatusWidths([-2, -1])
        # statusbar fields
        statusbar_fields = [("ButtonPanel wxPython Demo, Andrea Gavana @ 02 Oct 2006"),
            ("Welcome To wxPython!")]

        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        self.mainPanel = wx.Panel(self, -1)
        self.logtext = wx.TextCtrl(self.mainPanel, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY)

        vSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainPanel.SetSizer(vSizer)

        self.alignments = [bp.BP_ALIGN_LEFT, bp.BP_ALIGN_RIGHT, bp.BP_ALIGN_TOP, bp.BP_ALIGN_BOTTOM]

        self.alignment = bp.BP_ALIGN_LEFT
        self.agwStyle = bp.BP_USE_GRADIENT

        self.titleBar = bp.ButtonPanel(self.mainPanel, -1, "A Simple Test & Demo",
            agwStyle=self.agwStyle, alignment=self.alignment)

        self.created = False
        self.pngs = [ (images._bp_btn1.GetBitmap(), 'label1'),
            (images._bp_btn2.GetBitmap(), 'label2'),
            (images._bp_btn3.GetBitmap(), 'label3'),
            (images._bp_btn4.GetBitmap(), 'label4'),
        ]
        self.CreateButtons()
        self.SetProperties()


    def CreateMenuBar(self):

        mb = wx.MenuBar()

        file_menu = wx.Menu()

        item = wx.MenuItem(file_menu, wx.ID_ANY, "&Quit")
        file_menu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnClose, item)

        edit_menu = wx.Menu()

        item = wx.MenuItem(edit_menu, wx.ID_ANY, "Set Bar Text")
        edit_menu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnSetBarText, item)

        edit_menu.AppendSeparator()

        submenu = wx.Menu()

        item = wx.MenuItem(submenu, wx.ID_ANY, "BP_ALIGN_LEFT", kind=wx.ITEM_RADIO)
        submenu.AppendItem(item)
        item.Check(True)
        self.Bind(wx.EVT_MENU, self.OnAlignment, item)

        item = wx.MenuItem(submenu, wx.ID_ANY, "BP_ALIGN_RIGHT", kind=wx.ITEM_RADIO)
        submenu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnAlignment, item)

        item = wx.MenuItem(submenu, wx.ID_ANY, "BP_ALIGN_TOP", kind=wx.ITEM_RADIO)
        submenu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnAlignment, item)

        item = wx.MenuItem(submenu, wx.ID_ANY, "BP_ALIGN_BOTTOM", kind=wx.ITEM_RADIO)
        submenu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnAlignment, item)

        edit_menu.AppendMenu(wx.ID_ANY, "&Alignment", submenu)

        submenu = wx.Menu()

        item = wx.MenuItem(submenu, wx.ID_ANY, "Default Style", kind=wx.ITEM_RADIO)
        submenu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnDefaultStyle, item)

        item = wx.MenuItem(submenu, wx.ID_ANY, "Gradient Style", kind=wx.ITEM_RADIO)
        submenu.AppendItem(item)
        item.Check(True)
        self.Bind(wx.EVT_MENU, self.OnGradientStyle, item)

        edit_menu.AppendMenu(wx.ID_ANY, "&Styles", submenu)

        edit_menu.AppendSeparator()

        item = wx.MenuItem(submenu, wx.ID_ANY, "Settings Panel")
        edit_menu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnSettingsPanel, item)

        demo_menu = wx.Menu()

        item = wx.MenuItem(demo_menu, wx.ID_ANY, "Default Demo", kind=wx.ITEM_RADIO)
        demo_menu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnDefaultDemo, item)

        item = wx.MenuItem(demo_menu, wx.ID_ANY, "Button Only Demo", kind=wx.ITEM_RADIO)
        demo_menu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnButtonOnly, item)

        help_menu = wx.Menu()

        item = wx.MenuItem(help_menu, wx.ID_ANY, "&About...")
        help_menu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnAbout, item)

        mb.Append(file_menu, "&File")
        mb.Append(edit_menu, "&Edit")
        mb.Append(demo_menu, "&Demo")
        mb.Append(help_menu, "&Help")

        self.SetMenuBar(mb)


    def CreateButtons(self):

        # Here we (re)create the buttons for the default startup demo
        self.Freeze()

        if self.created:
            sizer = self.mainPanel.GetSizer()
            sizer.Detach(0)
            self.titleBar.Hide()
            wx.CallAfter(self.titleBar.Destroy)
            self.titleBar = bp.ButtonPanel(self.mainPanel, -1, "A Simple Test & Demo",
                agwStyle=self.agwStyle, alignment=self.alignment)
            self.SetProperties()

        self.indices = []

        for count, png in enumerate(self.pngs):

            shortHelp = "Button %d"%(count+1)

            if count < 2:
                # First 2 buttons are togglebuttons
                kind = wx.ITEM_CHECK
                longHelp = "ButtonPanel Toggle Button No %d"%(count+1)
            else:
                kind = wx.ITEM_NORMAL
                longHelp = "Simple Button without label No %d"%(count+1)

            btn = bp.ButtonInfo(self.titleBar, wx.NewId(),
                png[0], kind=kind,
                shortHelp=shortHelp, longHelp=longHelp)

            self.titleBar.AddButton(btn)
            self.Bind(wx.EVT_BUTTON, self.OnButton, id=btn.GetId())

            self.indices.append(btn.GetId())

            if count < 2:
                # First 2 buttons have also a text
                btn.SetText(png[1])

            if count == 2:
                # Append a separator after the second button
                self.titleBar.AddSeparator()

            if count == 1:
                # Add a wx.TextCtrl to ButtonPanel
                self.titleBar.AddControl(wx.TextCtrl(self.titleBar, -1, "Hello wxPython!"))
                btn.SetTextAlignment(bp.BP_BUTTONTEXT_ALIGN_RIGHT)

        # Add a wx.Choice to ButtonPanel
        self.titleBar.AddControl(wx.Choice(self.titleBar, -1,
            choices=["Hello", "From", "wxPython!"]))

        self.strings = ["First", "Second", "Third", "Fourth"]

        self.ChangeLayout()
        self.Thaw()
        self.titleBar.DoLayout()

        self.created = True


    def ButtonOnly(self):

        # Here we (re)create the buttons for the button-only demo
        self.Freeze()

        if self.created:
            sizer = self.mainPanel.GetSizer()
            sizer.Detach(0)
            self.titleBar.Hide()
            wx.CallAfter(self.titleBar.Destroy)
            self.titleBar = bp.ButtonPanel(self.mainPanel, -1, "A Simple Test & Demo",
                agwStyle=self.agwStyle, alignment=self.alignment)
            self.SetProperties()

        # Buttons are created completely random, with random images, toggle behavior
        # and text

        self.indices = []

        for count in xrange(8):

            itemImage = random.randint(0, 3)
            hasText = random.randint(0, 1)
            itemKind = random.randint(0, 1)

            btn = bp.ButtonInfo(self.titleBar, wx.NewId(), self.pngs[itemImage][0],
                kind=itemKind)

            if hasText:
                btn.SetText(self.pngs[itemImage][1])
                rightText = random.randint(0, 1)
                if rightText:
                    btn.SetTextAlignment(bp.BP_BUTTONTEXT_ALIGN_RIGHT)

            self.titleBar.AddButton(btn)
            self.Bind(wx.EVT_BUTTON, self.OnButton, id=btn.GetId())

            self.indices.append(btn.GetId())

            if count in [0, 3, 5]:
                self.titleBar.AddSeparator()

        self.strings = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth"]

        self.ChangeLayout()
        self.Thaw()
        self.titleBar.DoLayout()


    def ChangeLayout(self):

        # Change the layout after a switch in ButtonPanel alignment
        self.Freeze()

        if self.alignment in [bp.BP_ALIGN_LEFT, bp.BP_ALIGN_RIGHT]:
            vSizer = wx.BoxSizer(wx.VERTICAL)
        else:
            vSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.mainPanel.SetSizer(vSizer)

        vSizer.Add(self.titleBar, 0, wx.EXPAND)
        vSizer.Add((20, 20))
        vSizer.Add(self.logtext, 1, wx.EXPAND|wx.ALL, 5)

        vSizer.Layout()
        self.mainPanel.Layout()
        self.Thaw()


    def SetProperties(self):

        # No resetting if the user is using the Settings Panel
        if self.useredited:
            return

        # Sets the colours for the two demos: called only if the user didn't
        # modify the colours and sizes using the Settings Panel
        bpArt = self.titleBar.GetBPArt()

        if self.agwStyle & bp.BP_USE_GRADIENT:
            # set the colour the text is drawn with
            bpArt.SetColour(bp.BP_TEXT_COLOUR, wx.WHITE)

            # These default to white and whatever is set in the system
            # settings for the wx.SYS_COLOUR_ACTIVECAPTION.  We'll use
            # some specific settings to ensure a consistent look for the
            # demo.
            bpArt.SetColour(bp.BP_BORDER_COLOUR, wx.Colour(120,23,224))
            bpArt.SetColour(bp.BP_GRADIENT_COLOUR_FROM, wx.Colour(60,11,112))
            bpArt.SetColour(bp.BP_GRADIENT_COLOUR_TO, wx.Colour(120,23,224))
            bpArt.SetColour(bp.BP_BUTTONTEXT_COLOUR, wx.Colour(70,143,255))
            bpArt.SetColour(bp.BP_SEPARATOR_COLOUR,
                bp.BrightenColour(wx.Colour(60, 11, 112), 0.85))
            bpArt.SetColour(bp.BP_SELECTION_BRUSH_COLOUR, wx.Colour(225, 225, 255))
            bpArt.SetColour(bp.BP_SELECTION_PEN_COLOUR, wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVECAPTION))

        else:

            background = self.titleBar.GetBackgroundColour()
            bpArt.SetColour(bp.BP_TEXT_COLOUR, wx.BLUE)
            bpArt.SetColour(bp.BP_BORDER_COLOUR,
                bp.BrightenColour(background, 0.85))
            bpArt.SetColour(bp.BP_SEPARATOR_COLOUR,
                bp.BrightenColour(background, 0.85))
            bpArt.SetColour(bp.BP_BUTTONTEXT_COLOUR, wx.BLACK)
            bpArt.SetColour(bp.BP_SELECTION_BRUSH_COLOUR, wx.Colour(242, 242, 235))
            bpArt.SetColour(bp.BP_SELECTION_PEN_COLOUR, wx.Colour(206, 206, 195))

        self.titleBar.SetStyle(self.agwStyle)


    def OnAlignment(self, event):

        # Here we change the alignment property of ButtonPanel
        current = event.GetId()
        item = self.GetMenuBar().FindItemById(current)
        alignment = getattr(bp, item.GetLabel())
        self.alignment = alignment

        self.ChangeLayout()
        self.titleBar.SetAlignment(alignment)
        self.mainPanel.Layout()

        event.Skip()


    def OnDefaultStyle(self, event):

        # Restore the ButtonPanel default style (no gradient)
        self.agwStyle = bp.BP_DEFAULT_STYLE
        self.SetProperties()

        event.Skip()


    def OnGradientStyle(self, event):

        # Use gradients to paint ButtonPanel background
        self.agwStyle = bp.BP_USE_GRADIENT
        self.SetProperties()

        event.Skip()


    def OnDefaultDemo(self, event):

        # Reload the default startup demo
        self.CreateButtons()
        event.Skip()


    def OnButtonOnly(self, event):

        # Reload the button-only demo
        self.ButtonOnly()
        event.Skip()


    def OnButton(self, event):

        btn = event.GetId()
        indx = self.indices.index(btn)

        self.logtext.AppendText("Event Fired From " + self.strings[indx] + " Button\n")
        event.Skip()


    def OnSetBarText(self, event):

        dlg = wx.TextEntryDialog(self, "Enter The Text You Wish To Display On The Bar (Clear If No Text):",
            "Set Text", self.titleBar.GetBarText())

        if dlg.ShowModal() == wx.ID_OK:

            val = dlg.GetValue()
            self.titleBar.SetBarText(val)
            self.titleBar.DoLayout()
            self.mainPanel.Layout()


    def OnSettingsPanel(self, event):

        if self.hassettingpanel:
            self.settingspanel.Raise()
            return

        self.settingspanel = SettingsPanel(self, -1)
        self.settingspanel.Show()
        self.hassettingpanel = True


    def OnClose(self, event):

        self.Destroy()
        event.Skip()


    def OnAbout(self, event):

        msg = "This Is The About Dialog Of The ButtonPanel Demo.\n\n" +\
              "Author: Andrea Gavana @ 02 Oct 2006\n\n" +\
              "Please Report Any Bug/Requests Of Improvements\n" +\
              "To Me At The Following Adresses:\n\n" +\
              "andrea.gavana@gmail.com\n" + "gavana@kpo.kz\n\n" +\
              "Based On Eran C++ Implementation (wxWidgets Forum).\n\n" +\
              "Welcome To wxPython " + wx.VERSION_STRING + "!!"

        dlg = wx.MessageDialog(self, msg, "ButtonPanel wxPython Demo",
            wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()


    #----------------------------------------------------------------------

class TestPanel(wx.Panel):
    def __init__(self, parent, log):
        self.log = log
        wx.Panel.__init__(self, parent, -1)

        b = wx.Button(self, -1, " Test ButtonPanel ", (50,50))
        self.Bind(wx.EVT_BUTTON, self.OnButton, b)


    def OnButton(self, evt):
        self.win = ButtonPanelDemo(self)
        self.win.Show(True)


#----------------------------------------------------------------------

def runTest(frame, nb, log):
    win = TestPanel(nb, log)
    return win

#----------------------------------------------------------------------



overview = bp.__doc__



if __name__ == '__main__':
    import sys,os
    import run
    run.main(['', os.path.basename(sys.argv[0])] + sys.argv[1:])



