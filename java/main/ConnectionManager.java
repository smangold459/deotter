/*
 * Copyright 2026 Shane R. Mangold
 *
 * Licensed under the Apache License, Version 2.0.
 * See http://www.apache.org/licenses/LICENSE-2.0 or LICENSE file for details.
 */

//Manages Connections
package com.deotter.db;

import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.util.Properties;
import java.util.List;
import java.util.ArrayList;

public class ConnectionManager {
    private static ConnectionManager instance;

    private final Properties props = new Properties();
    private ConnectionProvider provider;

    private ConnectionManager() throws Exception {
        // constructs with Connection Provider object
        loadConfig();
        this.provider = new DirectConnectionProvider(props); // default for now
    }

    public static synchronized ConnectionManager getInstance() throws Exception {
        // singleton ConnectionManager
        if (instance == null) {
            instance = new ConnectionManager();
        }
        return instance;
    }

    public Connection getConnection(String alias) throws SQLException {
        return provider.getConnection(alias);
    }

    public String[] getAvailableDatabases() {
        String dbList = props.getProperty("databases", "");

        if (dbList.trim().isEmpty()) {
            return new String[0];
        }

        // split dbs into Java Array
        String[] databases = dbList.split(",");

        // clean whitespace
        for (int i = 0; i < databases.length; i++) {
            databases[i] = databases[i].trim();
        }

        return databases;
    }

    public void setProvider(ConnectionProvider newProvider) {
        // swap out from default connection provider
        this.provider = newProvider;
    }

    private void loadConfig() throws Exception {
        // get config.properties file
        String configPath = Paths.get(
            System.getProperty("user.home"), ".config", "deotter", "config.properties"
        ).toString();

        try (FileInputStream fis = new FileInputStream(configPath)) {
            this.props.load(fis);
            System.out.println("Loaded config from:" + configPath);
        } catch (IOException e) {
            throw new Exception("Could not find or read config file: " + configPath, e);
        }
    }

    public Object[][] fetchAllRows(ResultSet rs) throws SQLException {
        ResultSetMetaData meta = rs.getMetaData();
        int cols = meta.getColumnCount();

        // Use list to hold rows temporarily
        List<Object[]> rows = new ArrayList<>();
        while (rs.next()) {
            Object[] row = new Object[cols];
            for (int i=1; i <= cols; i++) {
                row[i - 1] = rs.getObject(i);
            }
            rows.add(row);
        }
        // Return as 2D array
        return rows.toArray(new Object[0][0]);
    }

    public Object[][] fetchManyRows(ResultSet rs, int limit) throws SQLException {
        ResultSetMetaData meta = rs.getMetaData();
        int cols = meta.getColumnCount();

        List<Object[]> rows = new ArrayList<>();
        int count = 0;

        // loop until the limit or rows expire
        while (count < limit && rs.next()) {
            Object[] row = new Object[cols];
            for (int i = 1; i <= cols; i++) {
                row [i -1] = rs.getObject(i);
            }
            rows.add(row);
            count++;
        }
        return rows.toArray(new Object[0][0]);
    }
}
