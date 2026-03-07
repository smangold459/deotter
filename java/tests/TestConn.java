package com.deotter.tests;

import com.deotter.db.ConnectionManager;
import java.sql.Connection;
import java.sql.SQLException;

public class TestConn {
    public static void main(String[] args) {
        try {
            // get connection manager
            ConnectionManager mgr = ConnectionManager.getInstance();

            // read config
            String[] databases = mgr.getAvailableDatabases();

            if (databases.length == 0) {
                System.out.println("No datbaases found. check 'databases=' in config.properties");
                return;
            }

            // loop through and test connections
            for (String db : databases) {
                System.out.println("\n--- Testing Alias: [" + db + "] ---");

                try (Connection conn = mgr.getConnection(db)) {
                    if (conn != null) {
                        System.out.println("SUCCESS: Connected to " + db);
                        System.out.println("DBMS: " + conn.getMetaData().getDatabaseProductName());
                    }
                } catch (SQLExc ption e) {
                    System.err.println("FAILED: Could not connect to " + db);
                    System.err.println("Error: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            System.err.println("CRITICAL: ConnectionManager failed to init.");
            e.printStackTrace();
        }
    }
}
