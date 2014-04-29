
class Globals():

    class __impl:
        def __init__(self):
            self.account_id = -1
            self.key_id = -1
            self.openport_address = "www.openport.be"

    # storage for the instance reference
    __instance = None

    def __init__(self):
        if Globals.__instance is None:
            # Create and remember instance
            Globals.__instance = Globals.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_Globals__instance'] = Globals.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
