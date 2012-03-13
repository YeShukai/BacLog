-- BacLog Copyright 2010-2012 by Timothy Middelkoop licensed under the Apache License 2.0
-- Database Schema v3+

-- BACnet device at the time of use (IP devices)
DROP TABLE IF EXISTS Devices;
CREATE TABLE Devices (
	deviceID SERIAL, 					-- Internal device ID
	IP inet,
	port integer,
	network integer, 					-- BACnet network number (should be the same)
	device integer, 					-- device instance (unique to network)
	name varchar, 						-- device description
	first timestamp with time zone,	 	-- first seen
	last timestamp  with time zone, 	-- valid until (NULL indicates live object)
	CONSTRAINT Devices_PK PRIMARY KEY (deviceID)
);

-- Points.  Physical equipment maped to an object a point in time.
DROP TABLE IF EXISTS Points;
CREATE TABLE Points ( 
	pointID SERIAL, 					-- Internal point ID
	name varchar, 						-- Full point name
	building char(32), 					-- Building Name
	room char(32), 						-- Room number/location
	unit char(32), 						-- Sensor, actuator, or device name/number
	description varchar, 				-- Description example: ROOM TEMP
	first timestamp with time zone, 	-- first seen
	last timestamp  with time zone, 	-- valid until (NULL indicates live point)
	CONSTRAINT Points_PK PRIMARY KEY (pointID)
);

-- BACnet points at the time of use.
DROP TABLE IF EXISTS Objects;
CREATE TABLE Objects (
	objectID SERIAL, 					-- object ID - object definition (temporal)
	deviceID integer, 					-- device ID - device definition (temporal)
	pointID integer, 					-- point ID - physical point definition
	type integer, 						-- BACnet objectType
	instance integer, 					-- BACnet objectInstance
	name varchar,		      			-- BACnet objectName
	description varchar,				-- BACnet description
	first timestamp with time zone, 	-- first time seen, valid until last
	last timestamp  with time zone, 	-- last time seen (NULL indicates live object)
	CONSTRAINT Objects_PK PRIMARY KEY (objectID)
);

-- Log Data
DROP TABLE IF EXISTS Log;
CREATE TABLE Log (
	time timestamp with time zone,		-- time measurement occured.
	IP inet, 							-- remote IP
	port integer,		 				-- remote port
	objectID integer, 					-- objectID
	type integer,						-- remote object type
	instance integer,			 		-- remote object instance
	status integer, 					-- what happened COV/ERROR etc.
	value real 							-- recorded value
);

CREATE INDEX i_Log_time ON Log (time);

-- Schedule program (Bacset side)
DROP TABLE IF EXISTS Schedule;
CREATE TABLE Schedule (
	scheduleID SERIAL,					-- schedule ID - order of schedule
	objectID integer,					-- object/device to control
	active timestamp with time zone,	-- set value after this time
	until timestamp with time zone,		-- do not set after this value
	value real,							-- set to value
	CONSTRAINT Schedule_PK PRIMARY KEY (scheduleID)
);

-- Control plan (baclog side, refactored/duplicated)
DROP TABLE IF EXISTS Control;
CREATE TABLE Control (
	scheduleID integer,					-- Control based on this schedule
	objectID integer,					-- object to be controled
	active timestamp with time zone,	-- control start
	until timestamp with time zone,		-- control end
	value integer,						-- control value
	enable boolean,						-- control active
	disable boolean,						-- control overriden or released
	CONSTRAINT Control_PK PRIMARY KEY (scheduleID)
);

-- Command Log -- commands written to device.
DROP TABLE IF EXISTS Commands;
CREATE TABLE Commands (
	commandID SERIAL,					-- command handle for updates.
	scheduleID integer, 				-- commanded due to schedule
	time timestamp with time zone,		-- commanded time
	IP inet, 							-- remote IP
	port integer,		 				-- remote port
	device integer,						-- remote device
	type integer,						-- remote object type
	instance integer,			 		-- remote object instance
	value real,							-- commanded value, NULL means release value
	priority integer,					-- priority of commanded value
	success boolean,					-- unit returned success
	verified boolean,					-- True if unit is at commanded value, NULL indicates no attempt.
	CONSTRAINT Command_PK PRIMARY KEY (commandID)
);

CREATE INDEX i_Commands_time ON Commands (time);
