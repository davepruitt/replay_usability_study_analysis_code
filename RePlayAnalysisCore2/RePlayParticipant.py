import persistent

class RePlayParticipant(persistent.Persistent):

    def __init__(self):
        self.uid = None
        self.visits = persistent.list.PersistentList()
        self.tags = persistent.mapping.PersistentMapping()

    def __str__(self):
        return self.uid

    def __repr__(self):
        return "{UID: " + f"{self.uid}" + ", Visit Count: " + f"{len(self.visits)}" + "}"
        
