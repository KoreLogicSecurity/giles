PRAGMA foreign_keys = 1;
PRAGMA recursive_triggers = 1;

INSERT INTO Giles_PersonExists_Facts(Name, Age) VALUES('Rob', 34);
INSERT INTO Giles_PersonExists_Facts(Name, Age) VALUES('Joel', 30);

INSERT INTO Giles_AnimalExists_Facts(Name, Age) VALUES('Caboose', 6);
INSERT INTO Giles_AnimalExists_Facts(Name, Age) VALUES('Donut', 11);
INSERT INTO Giles_AnimalExists_Facts(Name, Age) VALUES('Vanna', 12);
INSERT INTO Giles_AnimalExists_Facts(Name, Age) VALUES('Leo', 7);
INSERT INTO Giles_AnimalExists_Facts(Name, Age) VALUES('June', 2);
INSERT INTO Giles_AnimalExists_Facts(Name, Age) VALUES('Franny', 8);

INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('Rob', 'Chez Rob');
INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('Joel', 'Casa del Joel');
INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('Caboose', 'Chez Rob');
INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('Donut', 'Chez Rob');
INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('Vanna', 'Chez Rob');
INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('June', 'Casa del Joel');
INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('Leo', 'Casa del Joel');
INSERT INTO Giles_Inhabits_Facts(Name, Domicile) VALUES('Franny', 'Casa del Joel');
