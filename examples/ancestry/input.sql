PRAGMA foreign_keys = 1;
PRAGMA recursive_triggers = 1;

INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Betsy', 'James');
INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Betsy', 'Marvin');
INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Rob', 'James');
INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Rob', 'Marvin');
INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Julie', 'Betsy');
INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Bob', 'Betsy');
INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Ann', 'Rob');
INSERT INTO Giles_IsAncestor_Facts(Ancestor, Descendant) VALUES('Jim', 'Rob');

