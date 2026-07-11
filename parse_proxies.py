import re

text = """
185.176.26.107	Show Ports	HTTP	Transparent	Almaty	
185.176.26.28	Show Ports	HTTP	Transparent	Almaty	
185.176.26.100	Show Ports	HTTP	Transparent	Almaty	
185.176.26.40	Show Ports	HTTP	Transparent	Almaty	
185.176.26.3	Show Ports	HTTP	Transparent	Almaty	
185.176.26.17	Show Ports	HTTP	Transparent	Almaty	
185.176.26.79	Show Ports	HTTP	Transparent	Almaty	
185.176.26.216	Show Ports	HTTP	Transparent	Almaty	
185.176.26.75	Show Ports	HTTP	Transparent	Almaty	
185.176.26.0	Show Ports	HTTP	Transparent	Almaty	
185.176.26.223	Show Ports	HTTP	Transparent	Almaty	
185.176.26.210	Show Ports	HTTP	Transparent	Almaty	
31.43.179.104	Show Ports	HTTP	Transparent		
31.43.179.235	Show Ports	HTTP	Transparent		
185.176.26.132	Show Ports	HTTP	Transparent	Almaty	
185.176.26.31	Show Ports	HTTP	Transparent	Almaty	
185.176.26.7	Show Ports	HTTP	Transparent	Almaty	
185.176.26.247	Show Ports	HTTP	Transparent	Almaty	
185.176.26.152	Show Ports	HTTP	Transparent	Almaty	
185.176.26.252	Show Ports	HTTP	Transparent	Almaty	
185.176.26.192	Show Ports	HTTP	Transparent	Almaty	
185.176.26.145	Show Ports	HTTP	Transparent	Almaty	
185.176.26.56	Show Ports	HTTP	Transparent	Almaty	
185.176.26.190	Show Ports	HTTP	Transparent	Almaty	
185.176.26.127	Show Ports	HTTP	Transparent	Almaty	
185.176.26.82	Show Ports	HTTP	Transparent	Almaty	
185.176.26.90	Show Ports	HTTP	Transparent	Almaty	
185.176.26.218	Show Ports	HTTP	Transparent	Almaty	
185.176.26.97	Show Ports	HTTP	Transparent	Almaty	
31.43.179.28	Show Ports	HTTP	Transparent		
31.43.179.34	Show Ports	HTTP	Transparent		
31.43.179.88	Show Ports	HTTP	Transparent		
31.43.179.9	Show Ports	HTTP	Transparent		
185.176.26.92	Show Ports	HTTP	Transparent	Almaty	
31.43.179.159	Show Ports	HTTP	Transparent		
31.43.179.159	Show Ports	HTTP	Transparent		
185.176.26.144	Show Ports	HTTP	Transparent	Almaty	
31.43.179.187	Show Ports	HTTP	Transparent		
31.43.179.49	Show Ports	HTTP	Transparent		
185.176.26.22	Show Ports	HTTP	Transparent	Almaty	
185.176.26.99	Show Ports	HTTP	Transparent	Almaty	
31.43.179.163	Show Ports	HTTP	Transparent		
185.176.26.243	Show Ports	HTTP	Transparent	Almaty	
185.176.26.126	Show Ports	HTTP	Transparent	Almaty	
185.176.26.188	Show Ports	HTTP	Transparent	Almaty	
31.43.179.151	Show Ports	HTTP	Transparent		
185.176.26.162	Show Ports	HTTP	Transparent	Almaty	
185.176.26.13	Show Ports	HTTP	Transparent	Almaty	
185.176.26.86	Show Ports	HTTP	Transparent	Almaty	
185.176.26.142	Show Ports	HTTP	Transparent	Almaty	
185.176.26.206	Show Ports	HTTP	Transparent	Almaty	
185.176.26.63	Show Ports	HTTP	Transparent	Almaty	
185.176.26.215	Show Ports	HTTP	Transparent	Almaty	
185.176.26.156	Show Ports	HTTP	Transparent	Almaty	
185.176.26.224	Show Ports	HTTP	Transparent	Almaty	
185.176.26.222	Show Ports	HTTP	Transparent	Almaty	
185.176.26.44	Show Ports	HTTP	Transparent	Almaty	
185.176.26.110	Show Ports	HTTP	Transparent	Almaty	
185.176.26.120	Show Ports	HTTP	Transparent	Almaty	
31.43.179.255	Show Ports	HTTP	Transparent		
185.176.26.30	Show Ports	HTTP	Transparent	Almaty	
185.176.26.36	Show Ports	HTTP	Transparent	Almaty	
31.43.179.173	Show Ports	HTTP	Transparent		
31.43.179.78	Show Ports	HTTP	Transparent		
31.43.179.237	Show Ports	HTTP	Transparent		
31.43.179.55	Show Ports	HTTP	Transparent		
31.43.179.67	Show Ports	HTTP	Transparent		
31.43.179.135	Show Ports	HTTP	Transparent		
31.43.179.224	Show Ports	HTTP	Transparent		
31.43.179.158	Show Ports	HTTP	Transparent		
31.43.179.4	Show Ports	HTTP	Transparent		
31.43.179.139	Show Ports	HTTP	Transparent		
31.43.179.15	Show Ports	HTTP	Transparent		
185.176.26.89	Show Ports	HTTP	Transparent	Almaty	
185.176.26.200	Show Ports	HTTP	Transparent	Almaty	
185.176.26.251	Show Ports	HTTP	Transparent	Almaty	
185.176.26.227	Show Ports	HTTP	Transparent	Almaty	
185.176.26.178	Show Ports	HTTP	Transparent	Almaty	
185.176.26.201	Show Ports	HTTP	Transparent	Almaty	
185.176.26.77	Show Ports	HTTP	Transparent	Almaty	
31.43.179.225	Show Ports	HTTP	Transparent		
185.176.26.88	Show Ports	HTTP	Transparent	Almaty	
185.176.26.158	Show Ports	HTTP	Transparent	Almaty	
31.43.179.180	Show Ports	HTTP	Transparent		
31.43.179.0	Show Ports	HTTP	Transparent		
31.43.179.16	Show Ports	HTTP	Transparent		
31.43.179.44	Show Ports	HTTP	Transparent		
31.43.179.85	Show Ports	HTTP	Transparent		
31.43.179.150	Show Ports	HTTP	Transparent		
31.43.179.236	Show Ports	HTTP	Transparent		
31.43.179.212	Show Ports	HTTP	Transparent		
185.176.26.122	Show Ports	HTTP	Transparent	Almaty	
31.43.179.247	Show Ports	HTTP	Transparent		
31.43.179.205	Show Ports	HTTP	Transparent		
31.43.179.66	Show Ports	HTTP	Transparent		
31.43.179.220	Show Ports	HTTP	Transparent		
31.43.179.54	Show Ports	HTTP	Transparent		
185.176.26.157	Show Ports	HTTP	Transparent	Almaty	
31.43.179.3	Show Ports	HTTP	Transparent		
31.43.179.179	Show Ports	HTTP	Transparent		
31.43.179.21	Show Ports	HTTP	Transparent		
31.43.179.53	Show Ports	HTTP	Transparent		
31.43.179.58	Show Ports	HTTP	Transparent		
31.43.179.80	Show Ports	HTTP	Transparent		
185.176.26.173	Show Ports	HTTP	Transparent	Almaty	
31.43.179.231	Show Ports	HTTP	Transparent		
185.176.26.117	Show Ports	HTTP	Transparent	Almaty	
185.176.26.221	Show Ports	HTTP	Transparent	Almaty	
185.176.26.180	Show Ports	HTTP	Transparent	Almaty	
185.176.26.253	Show Ports	HTTP	Transparent	Almaty	
185.176.26.14	Show Ports	HTTP	Transparent	Almaty	
185.176.26.46	Show Ports	HTTP	Transparent	Almaty	
185.176.26.70	Show Ports	HTTP	Transparent	Almaty	
185.176.26.72	Show Ports	HTTP	Transparent	Almaty	
185.176.26.177	Show Ports	HTTP	Transparent	Almaty	
185.176.26.29	Show Ports	HTTP	Transparent	Almaty	
185.176.26.128	Show Ports	HTTP	Transparent	Almaty	
185.176.26.27	Show Ports	HTTP	Transparent	Almaty	
185.176.26.146	Show Ports	HTTP	Transparent	Almaty	
185.176.26.153	Show Ports	HTTP	Transparent	Almaty	
185.176.26.96	Show Ports	HTTP	Transparent	Almaty	
185.176.26.106	Show Ports	HTTP	Transparent	Almaty	
185.176.26.60	Show Ports	HTTP	Transparent	Almaty	
185.176.26.121	Show Ports	HTTP	Transparent	Almaty	
185.176.26.116	Show Ports	HTTP	Transparent	Almaty	
31.43.179.108	Show Ports	HTTP	Transparent		
185.176.26.141	Show Ports	HTTP	Transparent	Almaty	
82.115.60.51	Show Ports	HTTP	Elite	Almaty	
31.43.179.253	Show Ports	HTTP	Transparent		
185.176.26.155	Show Ports	HTTP	Transparent	Almaty	
185.176.26.211	Show Ports	HTTP	Transparent	Almaty	
185.176.26.250	Show Ports	HTTP	Transparent	Almaty	
185.176.26.189	Show Ports	HTTP	Transparent	Almaty	
185.176.26.61	Show Ports	HTTP	Transparent	Almaty	
185.176.26.8	Show Ports	HTTP	Transparent	Almaty	
185.176.26.18	Show Ports	HTTP	Transparent	Almaty	
185.176.26.137	Show Ports	HTTP	Transparent	Almaty	
185.176.26.168	Show Ports	HTTP	Transparent	Almaty	
185.176.26.15	Show Ports	HTTP	Transparent	Almaty	
31.43.179.248	Show Ports	HTTP	Transparent		
31.43.179.248	Show Ports	HTTP	Transparent		
31.43.179.86	Show Ports	HTTP	Transparent		
31.43.179.208	Show Ports	HTTP	Transparent		
31.43.179.186	Show Ports	HTTP	Transparent		
31.43.179.244	Show Ports	HTTP	Transparent		
31.43.179.128	Show Ports	HTTP	Transparent		
31.43.179.154	Show Ports	HTTP	Transparent		
31.43.179.56	Show Ports	HTTP	Transparent		
31.43.179.240	Show Ports	HTTP	Transparent		
31.43.179.250	Show Ports	HTTP	Transparent		
31.43.179.143	Show Ports	HTTP	Transparent		
31.43.179.103	Show Ports	HTTP	Transparent		
31.43.179.223	Show Ports	HTTP	Transparent		
31.43.179.161	Show Ports	HTTP	Transparent		
31.43.179.209	Show Ports	HTTP	Transparent		
31.43.179.206	Show Ports	HTTP	Transparent		
31.43.179.112	Show Ports	HTTP	Transparent		
31.43.179.33	Show Ports	HTTP	Transparent		
31.43.179.178	Show Ports	HTTP	Transparent		
31.43.179.35	Show Ports	HTTP	Transparent		
31.43.179.95	Show Ports	HTTP	Transparent		
31.43.179.59	Show Ports	HTTP	Transparent		
31.43.179.25	Show Ports	HTTP	Transparent		
31.43.179.42	Show Ports	HTTP	Transparent		
31.43.179.5	Show Ports	HTTP	Transparent		
31.43.179.14	Show Ports	HTTP	Transparent		
31.43.179.7	Show Ports	HTTP	Transparent		
31.43.179.166	Show Ports	HTTP	Transparent		
31.43.179.110	Show Ports	HTTP	Transparent		
31.43.179.119	Show Ports	HTTP	Transparent		
31.43.179.219	Show Ports	HTTP	Transparent		
185.176.26.179	Show Ports	HTTP	Transparent	Almaty	
31.43.179.130	Show Ports	HTTP	Transparent		
31.43.179.132	Show Ports	HTTP	Transparent		
31.43.179.101	Show Ports	HTTP	Transparent		
31.43.179.198	Show Ports	HTTP	Transparent		
31.43.179.152	Show Ports	HTTP	Transparent		
31.43.179.27	Show Ports	HTTP	Transparent		
31.43.179.63	Show Ports	HTTP	Transparent		
31.43.179.77	Show Ports	HTTP	Transparent		
185.176.26.139	Show Ports	HTTP	Transparent	Almaty	
31.43.179.70	Show Ports	HTTP	Transparent		
185.176.26.175	Show Ports	HTTP	Transparent	Almaty	
31.43.179.196	Show Ports	HTTP	Transparent		
185.176.26.26	Show Ports	HTTP	Transparent	Almaty	
31.43.179.51	Show Ports	HTTP	Transparent		
31.43.179.170	Show Ports	HTTP	Transparent		
185.176.26.204	Show Ports	HTTP	Transparent	Almaty	
185.176.26.159	Show Ports	HTTP	Transparent	Almaty	
31.43.179.232	Show Ports	HTTP	Transparent		
31.43.179.89	Show Ports	HTTP	Transparent		
185.176.26.4	Show Ports	HTTP	Transparent	Almaty	
31.43.179.116	Show Ports	HTTP	Transparent		
185.176.26.68	Show Ports	HTTP	Transparent	Almaty	
185.176.26.109	Show Ports	HTTP	Transparent	Almaty	
185.176.26.59	Show Ports	HTTP	Transparent	Almaty	
185.176.26.217	Show Ports	HTTP	Transparent	Almaty	
185.176.26.42	Show Ports	HTTP	Transparent	Almaty	
31.43.179.129	Show Ports	HTTP	Transparent		
185.176.26.172	Show Ports	HTTP	Transparent	Almaty	
185.176.26.239	Show Ports	HTTP	Transparent	Almaty	
185.176.26.91	Show Ports	HTTP	Transparent	Almaty	
185.176.26.161	Show Ports	HTTP	Transparent	Almaty	
185.176.26.103	Show Ports	HTTP	Transparent	Almaty	
31.43.179.19	Show Ports	HTTP	Transparent		
185.176.26.73	Show Ports	HTTP	Transparent	Almaty	
185.176.26.52	Show Ports	HTTP	Transparent	Almaty	
185.176.26.78	Show Ports	HTTP	Transparent	Almaty	
185.176.26.74	Show Ports	HTTP	Transparent	Almaty	
185.176.26.124	Show Ports	HTTP	Transparent	Almaty	
31.43.179.123	Show Ports	HTTP	Transparent		
185.176.26.81	Show Ports	HTTP	Transparent	Almaty	
31.43.179.234	Show Ports	HTTP	Transparent		
31.43.179.175	Show Ports	HTTP	Transparent		
31.43.179.228	Show Ports	HTTP	Transparent		
185.176.26.147	Show Ports	HTTP	Transparent	Almaty	
185.176.26.197	Show Ports	HTTP	Transparent	Almaty	
185.176.26.230	Show Ports	HTTP	Transparent	Almaty	
185.176.26.1	Show Ports	HTTP	Transparent	Almaty	
31.43.179.188	Show Ports	HTTP	Transparent		
31.43.179.39	Show Ports	HTTP	Transparent		
31.43.179.241	Show Ports	HTTP	Transparent		
31.43.179.65	Show Ports	HTTP	Transparent		
31.43.179.202	Show Ports	HTTP	Transparent		
31.43.179.87	Show Ports	HTTP	Transparent		
31.43.179.111	Show Ports	HTTP	Transparent		
31.43.179.136	Show Ports	HTTP	Transparent		
31.43.179.221	Show Ports	HTTP	Transparent		
31.43.179.176	Show Ports	HTTP	Transparent		
31.43.179.50	Show Ports	HTTP	Transparent		
31.43.179.10	Show Ports	HTTP	Transparent		
31.43.179.251	Show Ports	HTTP	Transparent		
31.43.179.8	Show Ports	HTTP	Transparent		
31.43.179.140	Show Ports	HTTP	Transparent		
31.43.179.74	Show Ports	HTTP	Transparent		
31.43.179.192	Show Ports	HTTP	Transparent		
31.43.179.149	Show Ports	HTTP	Transparent		
31.43.179.64	Show Ports	HTTP	Transparent		
31.43.179.137	Show Ports	HTTP	Transparent		
31.43.179.245	Show Ports	HTTP	Transparent		
31.43.179.122	Show Ports	HTTP	Transparent		
31.43.179.191	Show Ports	HTTP	Transparent		
31.43.179.153	Show Ports	HTTP	Transparent		
31.43.179.92	Show Ports	HTTP	Transparent		
31.43.179.177	Show Ports	HTTP	Transparent		
31.43.179.20	Show Ports	HTTP	Transparent		
31.43.179.83	Show Ports	HTTP	Transparent		
31.43.179.105	Show Ports	HTTP	Transparent		
31.43.179.168	Show Ports	HTTP	Transparent		
31.43.179.164	Show Ports	HTTP	Transparent		
31.43.179.109	Show Ports	HTTP	Transparent		
185.176.26.209	Show Ports	HTTP	Transparent	Almaty	
185.176.26.45	Show Ports	HTTP	Transparent	Almaty	
185.176.26.94	Show Ports	HTTP	Transparent	Almaty	
185.176.26.9	Show Ports	HTTP	Transparent	Almaty	
31.43.179.75	Show Ports	HTTP	Transparent		
31.43.179.38	Show Ports	HTTP	Transparent		
31.43.179.114	Show Ports	HTTP	Transparent		
185.176.26.123	Show Ports	HTTP	Transparent	Almaty	
31.43.179.201	Show Ports	HTTP	Transparent		
31.43.179.93	Show Ports	HTTP	Transparent		
89.40.233.13	Show Ports	SOCKS5	Elite	Astana	
31.43.179.99	Show Ports	HTTP	Transparent		
31.43.179.45	Show Ports	HTTP	Transparent		
31.43.179.195	Show Ports	HTTP	Transparent		
31.43.179.216	Show Ports	HTTP	Transparent		
31.43.179.138	Show Ports	HTTP	Transparent		
31.43.179.155	Show Ports	HTTP	Transparent		
31.43.179.100	Show Ports	HTTP	Transparent		
31.43.179.22	Show Ports	HTTP	Transparent		
31.43.179.37	Show Ports	HTTP	Transparent		
31.43.179.249	Show Ports	HTTP	Transparent		
31.43.179.43	Show Ports	HTTP	Transparent		
31.43.179.239	Show Ports	HTTP	Transparent		
31.43.179.115	Show Ports	HTTP	Transparent		
31.43.179.214	Show Ports	HTTP	Transparent		
31.43.179.98	Show Ports	HTTP	Transparent		
31.43.179.148	Show Ports	HTTP	Transparent		
31.43.179.26	Show Ports	HTTP	Transparent		
31.43.179.107	Show Ports	HTTP	Transparent		
31.43.179.148	Show Ports	HTTP	Transparent		
31.43.179.26	Show Ports	HTTP	Transparent		
31.43.179.107	Show Ports	HTTP	Transparent		
31.43.179.17	Show Ports	HTTP	Transparent		
185.176.26.150	Show Ports	HTTP	Transparent	Almaty	
31.43.179.222	Show Ports	HTTP	Transparent		
31.43.179.167	Show Ports	HTTP	Transparent		
31.43.179.210	Show Ports	HTTP	Transparent		
31.43.179.229	Show Ports	HTTP	Transparent		
31.43.179.72	Show Ports	HTTP	Transparent		
31.43.179.226	Show Ports	HTTP	Transparent		
31.43.179.11	Show Ports	HTTP	Transparent		
31.43.179.200	Show Ports	HTTP	Transparent		
31.43.179.40	Show Ports	HTTP	Transparent		
31.43.179.126	Show Ports	HTTP	Transparent		
31.43.179.106	Show Ports	HTTP	Transparent		
31.43.179.79	Show Ports	HTTP	Transparent		
31.43.179.41	Show Ports	HTTP	Transparent		
31.43.179.62	Show Ports	HTTP	Transparent		
31.43.179.82	Show Ports	HTTP	Transparent		
31.43.179.68	Show Ports	HTTP	Transparent		
31.43.179.160	Show Ports	HTTP	Transparent		
31.43.179.133	Show Ports	HTTP	Transparent		
31.43.179.145	Show Ports	HTTP	Transparent		
31.43.179.46	Show Ports	HTTP	Transparent		
31.43.179.165	Show Ports	HTTP	Transparent		
31.43.179.12	Show Ports	HTTP	Transparent		
31.43.179.246	Show Ports	HTTP	Transparent		
31.43.179.117	Show Ports	HTTP	Transparent		
31.43.179.207	Show Ports	HTTP	Transparent		
31.43.179.169	Show Ports	HTTP	Transparent		
31.43.179.141	Show Ports	HTTP	Transparent		
31.43.179.174	Show Ports	HTTP	Transparent		
31.43.179.184	Show Ports	HTTP	Transparent		
31.43.179.218	Show Ports	HTTP	Transparent		
31.43.179.185	Show Ports	HTTP	Transparent		
31.43.179.81	Show Ports	HTTP	Transparent		
31.43.179.1	Show Ports	HTTP	Transparent		
31.43.179.13	Show Ports	HTTP	Transparent		
31.43.179.118	Show Ports	HTTP	Transparent		
31.43.179.71	Show Ports	HTTP	Transparent		
31.43.179.76	Show Ports	HTTP	Transparent		
31.43.179.211	Show Ports	HTTP	Transparent		
31.43.179.6	Show Ports	HTTP	Transparent		
31.43.179.213	Show Ports	HTTP	Transparent		
31.43.179.84	Show Ports	HTTP	Transparent		
31.43.179.171	Show Ports	HTTP	Transparent		
2.78.60.10	Show Ports	HTTPS	Elite		
31.43.179.23	Show Ports	HTTP	Transparent		
31.43.179.48	Show Ports	HTTP	Transparent		
31.43.179.238	Show Ports	HTTP	Transparent		
31.43.179.190	Show Ports	HTTP	Transparent		
31.43.179.215	Show Ports	HTTP	Transparent		
31.43.179.233	Show Ports	HTTP	Transparent		
31.43.179.217	Show Ports	HTTP	Transparent		
31.43.179.61	Show Ports	HTTP	Transparent		
31.43.179.172	Show Ports	HTTP	Transparent		
31.43.179.252	Show Ports	HTTP	Transparent		
31.43.179.57	Show Ports	HTTP	Transparent		
31.43.179.254	Show Ports	HTTP	Transparent		
31.43.179.60	Show Ports	HTTP	Transparent		
31.43.179.124	Show Ports	HTTP	Transparent		
31.43.179.131	Show Ports	HTTP	Transparent		
31.43.179.162	Show Ports	HTTP	Transparent		
31.43.179.94	Show Ports	HTTP	Transparent		
193.47.43.18	Show Ports	SOCKS5	Elite	Astana	
31.43.179.90	Show Ports	HTTP	Transparent		
31.43.179.102	Show Ports	HTTP	Transparent		
31.43.179.24	Show Ports	HTTP	Transparent		
31.43.179.29	Show Ports	HTTP	Transparent		
185.176.26.130	Show Ports	HTTP	Transparent	Almaty	
185.176.26.32	Show Ports	HTTP	Transparent	Almaty	
185.176.26.151	Show Ports	HTTP	Transparent	Almaty	
31.43.179.193	Show Ports	HTTP	Transparent		
185.176.26.55	Show Ports	HTTP	Transparent	Almaty	
185.176.26.187	Show Ports	HTTP	Transparent	Almaty	
185.176.26.149	Show Ports	HTTP	Transparent	Almaty	
185.176.26.21	Show Ports	HTTP	Transparent	Almaty	
185.176.26.58	Show Ports	HTTP	Transparent	Almaty	
185.176.26.246	Show Ports	HTTP	Transparent	Almaty	
185.176.26.154	Show Ports	HTTP	Transparent	Almaty	
31.43.179.134	Show Ports	HTTP	Transparent		
31.43.179.181	Show Ports	HTTP	Transparent		
31.43.179.157	Show Ports	HTTP	Transparent		
185.176.26.37	Show Ports	HTTP	Transparent	Almaty	
31.43.179.230	Show Ports	HTTP	Transparent		
31.43.179.189	Show Ports	HTTP	Transparent		
31.43.179.91	Show Ports	HTTP	Transparent		
31.43.179.227	Show Ports	HTTP	Transparent		
31.43.179.125	Show Ports	HTTP	Transparent		
31.43.179.182	Show Ports	HTTP	Transparent		
31.43.179.2	Show Ports	HTTP	Transparent		
185.176.26.39	Show Ports	HTTP	Transparent	Almaty	
31.43.179.127	Show Ports	HTTP	Transparent		
31.43.179.243	Show Ports	HTTP	Transparent		
31.43.179.52	Show Ports	HTTP	Transparent		
31.43.179.203	Show Ports	HTTP	Transparent		
31.43.179.96	Show Ports	HTTP	Transparent		
31.43.179.204	Show Ports	HTTP	Transparent		
31.43.179.32	Show Ports	HTTP	Transparent		
31.43.179.30	Show Ports	HTTP	Transparent		
31.43.179.121	Show Ports	HTTP	Transparent		
185.176.26.48	Show Ports	HTTP	Transparent	Almaty	
185.176.26.235	Show Ports	HTTP	Transparent	Almaty	
185.176.26.76	Show Ports	HTTP	Transparent	Almaty	
31.43.179.156	Show Ports	HTTP	Transparent		
31.43.179.36	Show Ports	HTTP	Transparent		
185.176.26.163	Show Ports	HTTP	Transparent	Almaty	
31.43.179.183	Show Ports	HTTP	Transparent		
31.43.179.18	Show Ports	HTTP	Transparent		
31.43.179.197	Show Ports	HTTP	Transparent		
185.176.26.105	Show Ports	HTTP	Transparent	Almaty	
31.43.179.47	Show Ports	HTTP	Transparent		
31.43.179.97	Show Ports	HTTP	Transparent		
31.43.179.194	Show Ports	HTTP	Transparent		
31.43.179.120	Show Ports	HTTP	Transparent		
31.43.179.144	Show Ports	HTTP	Transparent		
185.176.26.131	Show Ports	HTTP	Transparent	Almaty	
31.43.179.146	Show Ports	HTTP	Transparent		
31.43.179.113	Show Ports	HTTP	Transparent		
31.43.179.31	Show Ports	HTTP	Transparent		
185.176.26.232	Show Ports	HTTP	Transparent	Almaty	
185.176.26.20	Show Ports	HTTP	Transparent	Almaty	
185.176.26.207	Show Ports	HTTP	Transparent	Almaty	
185.176.26.98	Show Ports	HTTP	Transparent	Almaty	
185.176.26.170	Show Ports	HTTP	Transparent	Almaty	
31.43.179.69	Show Ports	HTTP	Transparent		
31.43.179.147	Show Ports	HTTP	Transparent		
185.176.26.2	Show Ports	HTTP	Transparent	Almaty	
185.176.26.255	Show Ports	HTTP	Transparent	Almaty	
185.176.26.143	Show Ports	HTTP	Transparent	Almaty	
185.176.26.214	Show Ports	HTTP	Transparent	Almaty	
185.176.26.240	Show Ports	HTTP	Transparent	Almaty	
185.176.26.50	Show Ports	HTTP	Transparent	Almaty	
185.176.26.111	Show Ports	HTTP	Transparent	Almaty	
185.176.26.129	Show Ports	HTTP	Transparent	Almaty	
31.43.179.73	Show Ports	HTTP	Transparent		
31.43.179.242	Show Ports	HTTP	Transparent		
31.43.179.142	Show Ports	HTTP	Transparent		
185.176.26.49	Show Ports	HTTP	Transparent	Almaty	
185.176.26.66	Show Ports	HTTP	Transparent	Almaty	
31.43.179.199	Show Ports	HTTP	Transparent		
"""

lines = text.split("\n")
new_proxies = []
for line in lines:
    match = re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+Show Ports\s+(HTTP|HTTPS|SOCKS5)', line, re.IGNORECASE)
    if match:
        ip = match.group(1)
        proto = match.group(2).lower()
        if proto == 'https':
            proto = 'http'
        new_proxies.append(f"{proto}://{ip}:80")

# Убираем дубли
new_proxies = list(dict.fromkeys(new_proxies))

with open('proxies.txt', 'a') as f:
    for p in new_proxies:
        f.write(p + "\n")

print(f"Added {len(new_proxies)} proxies.")
