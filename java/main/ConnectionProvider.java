package com.deotter.db;

import java.sql.Connection;
import java.sql.SQLException;

public interface ConnectionProvider {
    Connection getConnection(String alias) throws SQLException;
}
