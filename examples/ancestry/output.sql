PRAGMA foreign_keys = 1;
PRAGMA recursive_triggers = 1;

SELECT Ancestor FROM Giles_IsAncestor_Facts WHERE Descendant = 'Marvin';
