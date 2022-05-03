# here would be my tests, IF I HAD ANY

class TestMetadata:
    def test_metadata_extraction_all_projects(self):
        for proj_name, context in test_projects.items():
            pro = Project(get_path_to_test_project(proj_name))
            before = time()
            pro.parse()
            after = time()

            metadata = pro.metadata()
            metadata["parse_time"] = after - before

            for meta_key, expected_value in context.items():
                assert metadata[meta_key] == expected_value
