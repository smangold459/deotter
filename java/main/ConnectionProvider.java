/*
 * Copyright 2026 Shane R. Mangold
 *
 * Licensed under the Apache License, Version 2.0.
 * See http://www.apache.org/licenses/LICENSE-2.0 or LICENSE file for details.
 */

package com.deotter.db;

import java.sql.Connection;
import java.sql.SQLException;

public interface ConnectionProvider {
    Connection getConnection(String alias) throws SQLException;
}
