-- hamon_fetcher.client definition

CREATE TABLE `client` (
  `IP` varchar(15) NOT NULL,
  `LAST_CONN_DATE` datetime NOT NULL,
  `LAST_DISCONN_DATE` datetime DEFAULT NULL,
  `DISCONN_CNT` int(10) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`IP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


-- hamon_fetcher.`fetch` definition

CREATE TABLE `fetch` (
  `FETCH_NO` int(11) NOT NULL AUTO_INCREMENT,
  `FETCH_FILE_NO` varchar(100) DEFAULT NULL,
  `SENDER_IP` varchar(15) NOT NULL,
  `START_DATE` datetime NOT NULL,
  PRIMARY KEY (`FETCH_NO`)
) ENGINE=InnoDB AUTO_INCREMENT=266 DEFAULT CHARSET=utf8;


-- hamon_fetcher.fetch_fail_cause definition

CREATE TABLE `fetch_fail_cause` (
  `FETCH_NO` int(11) NOT NULL,
  `TARGET_IP` varchar(15) NOT NULL,
  `CAUSE_TYPE` varchar(128) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


-- hamon_fetcher.fetch_file definition

CREATE TABLE `fetch_file` (
  `FILE_NO` int(11) NOT NULL AUTO_INCREMENT,
  `FILE_NAME` varchar(128) NOT NULL,
  `FILE_EXT` varchar(16) NOT NULL,
  `FILE_SIZE` int(12) NOT NULL,
  `FILE_MD5` varchar(128) NOT NULL,
  `CREATOR_IP` varchar(15) NOT NULL,
  `CREATE_DATE` datetime NOT NULL,
  PRIMARY KEY (`FILE_NO`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8;


-- hamon_fetcher.fetch_result definition

CREATE TABLE `fetch_result` (
  `FETCH_NO` int(11) NOT NULL,
  `TARGET_IP` varchar(15) NOT NULL,
  `END_DATE` datetime NOT NULL,
  `SUCCESS_FLAG` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


-- hamon_fetcher.client_fetch definition

CREATE TABLE `client_fetch` (
  `FETCH_NO` int(11) NOT NULL,
  `IP` varchar(15) NOT NULL,
  `PATH` varchar(256) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;