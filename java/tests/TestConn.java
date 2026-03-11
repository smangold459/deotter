package com.deotter.tests;

import com.deotter.db.ConnectionManager;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public class TestConn {
    private static final int EXPECTED_IRIS_ROW_COUNT = 150;

    private static String resolveIrisTable(Connection conn) throws SQLException {
        String product = conn.getMetaData().getDatabaseProductName().toLowerCase();

        if (product.contains("postgresql")) {
            return "public.iris";
        }
        if (product.contains("microsoft sql server")) {
            return "dbo.iris";
        }
        return "iris";
    }

    private static void validateFixtureData(Connection conn) throws SQLException {
        String irisTable = resolveIrisTable(conn);
        int rowCount;

        try (Statement stmt = conn.createStatement()) {
            try (ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM " + irisTable)) {
                rs.next();
                rowCount = rs.getInt(1);
            }

            if (rowCount != EXPECTED_IRIS_ROW_COUNT) {
                throw new SQLException(
                    "Expected " + EXPECTED_IRIS_ROW_COUNT
                    + " iris rows in " + irisTable + " but found " + rowCount
                );
            }

            System.out.println("Fixture row count verified: " + rowCount);

            String groupedQuery =
                "SELECT species, COUNT(*) AS species_count "
                + "FROM " + irisTable + " "
                + "GROUP BY species "
                + "ORDER BY species";
            try (ResultSet rs = stmt.executeQuery(groupedQuery)) {
                while (rs.next()) {
                    System.out.println(
                        "  species=" + rs.getString(1) + ", count=" + rs.getInt(2)
                    );
                }
            }
        }
    }

    public static void main(String[] args) {
        boolean hasFailures = false;

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
                        validateFixtureData(conn);
                    }
                } catch (SQLException e) {
                    hasFailures = true;
                    System.err.println("FAILED: Could not connect to " + db);
                    System.err.println("Error: " + e.getMessage());
                }
            }

            if (hasFailures) {
                System.exit(1);
            }
        } catch (Exception e) {
            System.err.println("CRITICAL: ConnectionManager failed to init.");
            e.printStackTrace();
            System.exit(1);
        }
    }
}
