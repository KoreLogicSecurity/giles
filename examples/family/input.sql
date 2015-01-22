PRAGMA foreign_keys = 1;
PRAGMA recursive_triggers = 1;

INSERT INTO Giles_KnownFamilies_Facts(Family) VALUES('Jones');
INSERT INTO Giles_KnownFamilies_Facts(Family) VALUES('King');
INSERT INTO Giles_KnownFamilies_Facts(Family) VALUES('Smith');
INSERT INTO Giles_PersonIsNamed_Facts(FirstName, LastName) VALUES('Rob', 'King');
INSERT INTO Giles_PersonIsNamed_Facts(FirstName, LastName) VALUES('Betsy', 'King');
INSERT INTO Giles_PersonIsNamed_Facts(FirstName, LastName) VALUES('John', 'Smith');
INSERT INTO Giles_PersonIsNamed_Facts(FirstName, LastName) VALUES('John', 'Jones');
