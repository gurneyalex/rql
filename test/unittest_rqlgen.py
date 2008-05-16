"""
Copyright (c) 2000-2008 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from logilab.common.testlib import TestCase, DocTest, unittest_main

from rql import rqlgen

class RQLGenDocTest(DocTest):
    module = rqlgen

class RQLGenTC(TestCase):
    """tests the rqlgen behaviour
    """

    def setUp(self):
        """Only defines a rql generator
        """
        self.rql_generator = rqlgen.RQLGenerator()


    def test_select_etype(self):
        """tests select with entity type only
        """
        rql = self.rql_generator.select('Person')
        self.assertEquals(rql, 'Person X')
        

    def test_select_group(self):
        """tests select with group
        """
        rql = self.rql_generator.select('Person', groups=('X',))
        self.assertEquals(rql, 'Person X\nGROUPBY X')


    def test_select_sort(self):
        """tests select with sort
        """
        rql = self.rql_generator.select('Person', sorts=('X ASC',))
        self.assertEquals(rql, 'Person X\nSORTBY X ASC')


    def test_select(self):
        """tests select with e_type, attributes, sort, and group
        """
        rql = self.rql_generator.select('Person',
                                        ( ('X','work_for','S'),
                                          ('S','name','"Logilab"'),
                                          ('X','firstname','F'),
                                          ('X','surname','S') ),
                                        ('X',),
                                        ('F ASC', 'S DESC'))
        self.assertEquals(rql, 'Person X\nWHERE X work_for S , S name "Logilab"'
                          ' , X firstname F , X surname S\nGROUPBY X'
                          '\nSORTBY F ASC, S DESC')
                                        
        
    def test_where(self):
        """tests the where() method behaviour
        """
        rql = self.rql_generator.where(( ('X','work_for','S'),
                                         ('S','name','"Logilab"'),
                                         ('X','firstname','F'),
                                         ('X','surname','S') ) )
        self.assertEquals(rql, 'WHERE X work_for S , S name "Logilab" '
                          ', X firstname F , X surname S')


    def test_groupby(self):
        """tests the groupby() method behaviour
        """
        rql = self.rql_generator.groupby(('F', 'S'))
        self.assertEquals(rql, 'GROUPBY F, S')
        

    def test_sortby(self):
        """tests the sortby() method behaviour
        """
        rql = self.rql_generator.sortby(('F ASC', 'S DESC'))
        self.assertEquals(rql, 'SORTBY F ASC, S DESC')
        

    def test_insert(self):
        """tests the insert() method behaviour
        """
        rql = self.rql_generator.insert('Person', (('firstname', "Clark"),
                                                   ('lastname', "Kent")))
        self.assertEquals(rql, 'INSERT Person X: X firstname "Clark",'
                          ' X lastname "Kent"')
        
        
    def test_update(self):
        """tests the update() method behaviour
        """
        rql = self.rql_generator.update('Person',
                                        (('firstname', "Clark"),
                                         ('lastname', "Kent")),
                                        (('job', "superhero"),
                                         ('nick', "superman")))
        self.assertEquals(rql, 'SET X job "superhero", X nick "superman" '
                          'WHERE X is "Person", X firstname "Clark", X '
                          'lastname "Kent"')


    def test_delete(self):
        """tests the delete() method behaviour
        """
        rql = self.rql_generator.delete('Person',
                                        (('firstname', "Clark"),
                                         ('lastname', "Kent")))
        self.assertEquals(rql, 'DELETE Person X where X firstname "Clark", '
                          'X lastname "Kent"')
        
if __name__ == '__main__':
    unittest_main()
