-- hamon_fetcher.client_pc definition

CREATE TABLE `client_pc` (
  `IP` varchar(15) NOT NULL,
  `LAST_CONNECT_DATE` datetime NOT NULL,
  `LAST_DISCONNECT_DATE` datetime DEFAULT NULL,
  `DISCONNECT_COUNT` int(10) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`IP`)
);


-- hamon_fetcher.`fetch` definition

CREATE TABLE `fetch` (
  `FETCH_ID` int(11) NOT NULL AUTO_INCREMENT,
  `FILE_NAME` varchar(256) NOT NULL,
  `FILE_EXT` varchar(16) NOT NULL,
  `FILE_SIZE` varchar(32) NOT NULL,
  `CREATOR_IP` varchar(15) NOT NULL,
  `CREATE_DATE` datetime NOT NULL,
  PRIMARY KEY (`FETCH_ID`)
);


-- hamon_fetcher.fetch_fail_cause definition

CREATE TABLE `fetch_fail_cause` (
  `FETCH_ID` int(11) NOT NULL,
  `FETCHER_IP` varchar(15) NOT NULL,
  `START_DATE` datetime NOT NULL,
  `CAUSE_TYPE` varchar(128) NOT NULL,
  PRIMARY KEY (`FETCH_ID`,`FETCHER_IP`,`START_DATE`)
);


-- hamon_fetcher.fetch_result definition

CREATE TABLE `fetch_result` (
  `FETCH_ID` int(11) NOT NULL,
  `FETCHER_IP` varchar(15) NOT NULL,
  `START_DATE` datetime NOT NULL,
  `END_DATE` datetime NOT NULL,
  `COMPLETE_FLAG` tinyint(1) NOT NULL,
  PRIMARY KEY (`FETCH_ID`,`FETCHER_IP`,`START_DATE`)
);