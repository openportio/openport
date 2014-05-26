
class OpenPortGUI(object):
    def __init__(self):
        super(OpenPortGUI, self).__init__()
        from gui.shares_frame import SharesFrame
        self.shares_frame = SharesFrame(None, -1, "OpenPort", self)
        self.viewShares(None)

    def stop_sharing(self,share):
        super(OpenPortGUI, self).stop_sharing(share)
        wx.CallAfter( self.shares_frame.remove_share, share)

    def viewShares(self, event):
        self.shares_frame.Show(True)

    def onShareError(self, share):
        super(OpenPortGUI, self).onShareError(share)
        wx.CallAfter( self.shares_frame.notify_error, share)

    def onShareSuccess(self, share):
        super(OpenPortGUI, self).onShareSuccess(share)
        wx.CallAfter( self.shares_frame.notify_success, share)

    def onNewShare(self, share):
        super(OpenPortGUI, self).onNewShare(share)
        callbacks = {'stop': self.stop_sharing}
        wx.CallAfter( self.shares_frame.add_share, share, callbacks )

    def show_account_status(self, dict):
        wx.CallAfter( self.shares_frame.update_account,
            bytes_this_month = dict['bytes_this_month'],
            next_counter_reset_time = utc_epoch_to_local_datetime(dict['next_counter_reset_time']),
            max_bytes = dict['max_bytes']
        )