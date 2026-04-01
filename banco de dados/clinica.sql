INSERT INTO consultas (cliente_id, tipo_consulta, data, horario, status, medico_id) VALUES
(1, 'primeira_consulta', CURDATE(), '08:00:00', 'confirmado', 1),
(2, 'retorno',           CURDATE(), '09:00:00', 'confirmado', 1),
(3, 'primeira_consulta', CURDATE(), '10:00:00', 'pendente',   1),
(4, 'retorno',           CURDATE(), '11:00:00', 'confirmado', 1);