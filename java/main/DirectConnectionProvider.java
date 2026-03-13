/*
 * Copyright 2026 Shane R. Mangold
 *
 * Licensed under the Apache License, Version 2.0.
 * See http://www.apache.org/licenses/LICENSE-2.0 or LICENSE file for details.
 */

package com.deotter.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Properties;

public class DirectConnectionProvider implements ConnectionProvider {
    private final Properties props;
    
    public DirectConnectionProvider(Properties props) {
        this.props = props;
    }

    @Override
    public Connection getConnection(String alias) throws SQLException {
        String url = props.getProperty(alias + ".url");
        String user = props.getProperty(alias + ".user");
        String pass = props.getProperty(alias + ".password");

        if (url == null) {
            throw new SQLException("No configfureation found for alias: " + alias);
        }
        return DriverManager.getConnection(url, user, pass);
    }
}
