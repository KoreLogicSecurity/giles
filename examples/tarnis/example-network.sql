/**********************************************************************
 *
 * $Id$
 *
 **********************************************************************
 *
 * Copyright 2011-2014 KoreLogic, Inc. All Rights Reserved.
 *
 * This software, having been partly or wholly developed and/or
 * sponsored by KoreLogic, Inc., is hereby released under the terms
 * and conditions set forth in the project's "README.LICENSE" file.
 * For a list of all contributors and sponsors, please refer to the
 * project's "README.CREDITS" file.
 *
 **********************************************************************
 *
 * Purpose: Tarnis is an example expert system.
 *
 **********************************************************************
 */

/* Name our networks and assign each of them a security level. Note that we don't declare Network 1, we let Tarnis infer its existence. */
INSERT INTO Tarnis_NetworkExists_facts(NetworkName, SecurityLevel) VALUES('Network 2', 20);
INSERT INTO Tarnis_NetworkExists_facts(NetworkName, SecurityLevel) VALUES('Network 3', 30);
INSERT INTO Tarnis_NetworkExists_facts(NetworkName, SecurityLevel) VALUES('Network 4', 40);
INSERT INTO Tarnis_NetworkExists_facts(NetworkName, SecurityLevel) VALUES('Network 5', 50);
INSERT INTO Tarnis_NetworkExists_facts(NetworkName, SecurityLevel) VALUES('Network 6', 60);

/* Declare the network topology. All of the links are unidirectional, with information only flowing from less-secure to more-secure networks... */
INSERT INTO Tarnis_UnidirectionalNetworkConnection_facts(NetworkA, NetworkB) VALUES('Network 1', 'Network 2');
INSERT INTO Tarnis_UnidirectionalNetworkConnection_facts(NetworkA, NetworkB) VALUES('Network 2', 'Network 3');
INSERT INTO Tarnis_UnidirectionalNetworkConnection_facts(NetworkA, NetworkB) VALUES('Network 3', 'Network 4');
INSERT INTO Tarnis_UnidirectionalNetworkConnection_facts(NetworkA, NetworkB) VALUES('Network 4', 'Network 5');

/* ..except for a bidirectional link which allows backflow from network 5 to network 3, and therefore from 4 to 3 (by 4 -> 5 -> 3). */
INSERT INTO Tarnis_BidirectionalNetworkConnection_facts(NetworkA, NetworkB) VALUES('Network 3', 'Network 5');

/* This backflow is documented and exceptions were allowed. In other words, we want to tell Tarnis that we're aware of
 * traffic flowing from Network 5 to Network 3, and from Network 4 to Network 3, and that we are explicitly okay with it. */
INSERT INTO Tarnis_AllowException_facts(NetworkA, NetworkB) VALUES('Network 5', 'Network 3');
INSERT INTO Tarnis_AllowException_facts(NetworkA, NetworkB) VALUES('Network 4', 'Network 3');

/* But did you see the flaw? We've now allowed data to flow from 5 to 4, via the 5 -> 3 -> 4 path. This wasn't documented or explicitly allowed!
 * Let's see if Tarnis notices the problem and fires an alert:
 */

SELECT * FROM Tarnis_Alert_facts;

/* We also included Network 6 up there with no connections to anyone else, just to provide an "orphan network" alert.
 * Read tarnis.yml to see all of the different things we check for.
 *
 * What makes Tarnis such a good demonstration of Giles is that you can add or remove networks, bidirectional or unidirectional channels, exceptions,
 * and so on, and the system automatically maintains a list of alerts for issues that need to be addrressed. Alerts will go away if the problem goes
 * away or is remedied (via an exception for example), and will come back if the problem comes back.
 *
 * Try different remedies - add an explicit exception, break the link between 5 and 3 and so on.
 *
 * Tarnis, thanks to Giles, also can justify any event, including alerts.
 * We could justify an alert by asking: SELECT justification FROM Tarnis_Alert_justification WHERE id = <id>
 * That justification will include the facts that led to that event, so you can ask for their justifications, all the way back to the
 * initial, user-provided facts.
 */

